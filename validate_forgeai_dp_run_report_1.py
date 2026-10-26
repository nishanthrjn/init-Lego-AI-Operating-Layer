"""Maintainer-run offline report checks; no Docker, installs or live models."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGEAI = ROOT / "examples/forgeai"
BASE = "fd4b51580e69f6958741cd4ef1bd46f28ee6ac31"
SELF = "validate_forgeai_dp_run_report_1.py"
ALLOWED = frozenset(
    {
        SELF,
        "examples/forgeai/src/forgeai/report.py",
        "examples/forgeai/src/forgeai/cli.py",
        "examples/forgeai/tests/test_run_report.py",
        "examples/forgeai/tests/test_architecture.py",
        "examples/forgeai/tests/test_clean_install.py",
        "examples/forgeai/demo.py",
        "examples/forgeai/README.md",
    }
)
PRESERVED = (
    "scripts/forgeai_kisski_bounded_live_pilot.py",
    "packages",
    "src",
    "experiments",
    "planning",
    "adrs",
)
# Maintainer-approved exclusions: these historical tests do not all honor
# LEGOAI_QUALIFY_* and would execute Docker or build/install wheels on Windows.
INTEGRATION_FILES = (
    "tests/test_end_to_end.py",
    "tests/test_clean_install.py",
    "evaluation/tests/test_lq1_fixtures_docker.py",
    "evaluation/tests/test_lq1_diagnostics_docker.py",
)
OFFLINE_SELECTION = "not real_docker and not real_sandbox"


def git_phase(phase: str, env: dict[str, str]) -> None:
    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", *args],
            cwd=ROOT,
            env=env,
            text=True,
            encoding="utf-8",
            timeout=30,
        )

    if phase == "scope":
        changed = (
            set(git("diff", "--name-only", BASE).splitlines())
            | set(git("diff", "--cached", "--name-only", BASE).splitlines())
            | set(git("ls-files", "--others", "--exclude-standard").splitlines())
        )
        if changed - ALLOWED:
            raise ValueError("outside slice scope: " + repr(sorted(changed - ALLOWED)))
    elif phase == "preservation":
        git("diff", "--quiet", BASE, "--", *PRESERVED)
        git("diff", "--cached", "--quiet", BASE, "--", *PRESERVED)
    elif phase == "whitespace":
        git("diff", "--check")
        git("diff", "--cached", "--check")
    else:
        raise ValueError("unsupported internal phase")


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    for name in tuple(env):
        if name.startswith("LEGOAI_QUALIFY_"):
            env.pop(name)
    env["UV_OFFLINE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    # Match the existing pilot validator: its projection lives at repository root.
    import_paths = (str(ROOT), str(FORGEAI), str(FORGEAI / "src"))
    env["PYTHONPATH"] = os.pathsep.join(import_paths)
    env["MYPYPATH"] = str(ROOT)
    phase = "setup"
    uv = shutil.which("uv")

    def project(name: str, *args: str) -> None:
        nonlocal phase
        phase = name
        if uv is None:
            raise ValueError("uv required; existing locked environments required")
        print("\n[PHASE] " + name, flush=True)
        subprocess.run(
            [uv, "run", "--locked", "--offline", "--no-sync", "python", *args],
            cwd=FORGEAI,
            env=env,
            check=True,
        )

    try:
        if len(sys.argv) == 3 and sys.argv[1] == "--phase":
            phase = sys.argv[2]
            git_phase(phase, env)
            return 0
        if len(sys.argv) != 1:
            raise ValueError("no operator arguments supported")
        validator = str(ROOT / SELF)
        project("scope", validator, "--phase", "scope")
        project("preservation", validator, "--phase", "preservation")
        pytest = ("-m", "pytest", "-q", "-p", "no:cacheprovider")
        project("run report contracts", *pytest, "tests/test_run_report.py")
        project(
            "architecture, CLI and pilot regressions",
            *pytest,
            "tests/test_architecture.py",
            "tests/test_cli.py",
            "tests/test_kisski_bounded_live_pilot.py",
        )
        phase = "offline exclusion paths"
        for path in INTEGRATION_FILES:
            if not (FORGEAI / path).is_file():
                raise ValueError("excluded test file missing: " + path)
        print(
            "Offline regression exclusions (maintainer approved): "
            + ", ".join(INTEGRATION_FILES)
            + "; selection: "
            + OFFLINE_SELECTION,
            flush=True,
        )
        print(
            "EXCLUDED: evaluation/tests (historical evaluation harnesses; "
            "not touched by this slice; pre-existing failures tracked separately "
            "as FORGEAI-EVAL-HARNESS-TRIAGE-1)",
            flush=True,
        )
        print(
            "Product tests only; pytest reports skipped/deselected counts. "
            "This is not full integration or clean-install qualification.",
            flush=True,
        )
        project(
            "product suite, offline regressions only",
            *pytest,
            "tests",
            *("--ignore=" + path for path in INTEGRATION_FILES),
            "-k",
            OFFLINE_SELECTION,
        )
        project("strict typing", "-m", "mypy", "src", "tests", validator)
        project(
            "lint",
            "-m",
            "ruff",
            "check",
            "--no-cache",
            "--config",
            str(FORGEAI / "pyproject.toml"),
            "--config",
            'lint.isort.known-first-party = ["forgeai", "forgeai_eval", "scripts"]',
            "src",
            "tests",
            "demo.py",
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
            str(FORGEAI / "pyproject.toml"),
            "src",
            "tests",
            "demo.py",
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
        project("whitespace", validator, "--phase", "whitespace")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL [{phase}] {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-DP-RUN-REPORT-1 LOCAL CHECKS PASSED; "
        "REPLAY MODELS AND FAKE SANDBOX ONLY; MODEL QUALITY NOT QUALIFIED; "
        "NO LIVE EXECUTION"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
