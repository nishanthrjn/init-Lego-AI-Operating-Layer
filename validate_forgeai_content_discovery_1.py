r"""Offline CONTENT-DISCOVERY-1 qualification. Run uv run python .\validate_forgeai_content_discovery_1.py."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENGINEERING = ROOT / "packages/legoai-engineering"
BASE = "ee045fed663fa40f2939eb7e16d78b45e5110fe0"
PREFIX = "examples/forgeai/evaluation/content_discovery1/"
ALLOWED = {
    PREFIX + name
    for name in (
        "__init__.py",
        "data.py",
        "stages.py",
        "wiring.py",
        "evaluate.py",
        "fixtures-v1.json",
        "thresholds-v1.json",
        "preregistration-v1.json",
        "manifest-v1.json",
        "results-v1.json",
        "results-v1.md",
    )
} | {
    "examples/forgeai/evaluation/tests/test_content_discovery_1.py",
    "planning/FORGEAI-CONTENT-DISCOVERY-EVALUATION.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "validate_forgeai_content_discovery_1.py",
}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, encoding="utf-8", check=True
    ).stdout


def scope() -> None:
    changed = set(git("diff", "--name-only", BASE).splitlines())
    changed.update(
        git(
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            ".",
            ":(exclude)examples/forgeai/.lq13-test-temp/**",
        ).splitlines()
    )
    if changed - ALLOWED:
        raise RuntimeError("unexpected scope: " + repr(sorted(changed - ALLOWED)))


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(PYTHONDONTWRITEBYTECODE="1", UV_OFFLINE="1")
    phase = "1 scope guard / production non-interference"
    completed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="content-discovery-1-") as temporary:
        temp = Path(temporary)

        def run(name: str, cwd: Path, *args: str) -> None:
            nonlocal phase
            phase = name
            print("[PHASE] " + name, flush=True)
            subprocess.run(
                ["uv", "run", "--locked", "--no-sync", "python", "-B", "-m", *args],
                cwd=cwd,
                env=env,
                check=True,
            )
            completed.append(name)

        def tests(name: str, *selectors: str) -> None:
            run(
                name,
                FORGE,
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                *(
                    "evaluation/tests/test_content_discovery_1.py::" + s
                    for s in selectors
                ),
            )

        try:
            print("[PHASE] " + phase, flush=True)
            scope()
            completed.append(phase)
            tests("2 frozen DISCOVERY immutability", "test_freeze")
            tests("3 fixture schema", "test_freeze", "test_read_truth")
            tests("4 read ground truth", "test_read_truth")
            tests("5 frozen thresholds", "test_freeze")
            tests("6 deterministic read proposal", "test_confirmed_request")
            tests("7 operator confirmation", "test_confirmation_operations")
            tests(
                "8 authorized evidence reuse",
                "test_confirmed_request",
                "test_limits_and_missing",
            )
            tests(
                "9 authorization failures",
                "test_authorization_failure",
                "test_final_release_denial",
            )
            tests("10 Analyst request boundary", "test_confirmed_request")
            tests(
                "11 interpretation and staleness",
                "test_narrative_and_unknown_path",
                "test_staleness",
            )
            tests(
                "12 no target authority expansion",
                "test_target_interpretation_and_authority",
            )
            tests("13 CREATE", "test_create_and_correction_metrics")
            tests("14 matched reference", "test_matched_and_folding")
            tests(
                "15 metrics",
                "test_create_and_correction_metrics",
                "test_matched_and_folding",
            )
            tests("16 aggregate folding", "test_matched_and_folding")
            tests("17 privacy and reproduction", "test_report_privacy_reproduction")
            run(
                "18 DISCOVERY-1 regressions",
                ENGINEERING,
                "pytest",
                "-q",
                "-rs",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(temp / "structure"),
                "tests/test_structure.py",
                "tests/test_architecture.py",
            )
            run(
                "19 DISCOVERY-2A/2A.1 regressions",
                FORGE,
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "evaluation/tests/test_discovery_2a.py",
                "evaluation/tests/test_discovery_2a1.py",
            )
            run(
                "20 Analyst/evidence regressions",
                ENGINEERING,
                "pytest",
                "-q",
                "-rs",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(temp / "analyst"),
                "tests/test_analyst.py",
                "tests/test_analyst_architecture.py",
                "tests/test_authorized_effects.py",
            )
            run(
                "21 ForgeAI architecture and content evaluation",
                FORGE,
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_architecture.py",
                "evaluation/tests/test_lq1_architecture.py",
                "evaluation/tests/test_content_discovery_1.py",
            )
            run(
                "22 mypy",
                FORGE,
                "mypy",
                "--cache-dir",
                str(temp / "mypy"),
                "evaluation/content_discovery1",
                "evaluation/tests/test_content_discovery_1.py",
                str(ROOT / "validate_forgeai_content_discovery_1.py"),
            )
            run(
                "23 Ruff lint",
                FORGE,
                "ruff",
                "check",
                "--no-cache",
                "evaluation/content_discovery1",
                "evaluation/tests/test_content_discovery_1.py",
                str(ROOT / "validate_forgeai_content_discovery_1.py"),
            )
            run(
                "24 Ruff format",
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                "evaluation/content_discovery1",
                "evaluation/tests/test_content_discovery_1.py",
                str(ROOT / "validate_forgeai_content_discovery_1.py"),
            )
            phase = "25 git diff check"
            subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
            completed.append(phase)
        except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
            print(f"FAIL {phase}: {error}; later phases NOT RUN")
            return 1
    for item in completed:
        print("PASS " + item)
    print(
        "CONTENT-DISCOVERY-1 LOCAL VALIDATION PASSED - scripted replay; no live model; no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
