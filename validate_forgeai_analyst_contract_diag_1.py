r"""Offline ANALYST-CONTRACT-DIAG-1 qualification. No live model, no Docker.

uv run python .\validate_forgeai_analyst_contract_diag_1.py
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENGINEERING = ROOT / "packages/legoai-engineering"
BASE = "6df48a1"  # CONTENT-DISCOVERY-1Q result recorded
PREFIX = "examples/forgeai/evaluation/analyst_contract_diag1/"
TESTS = "evaluation/tests/test_analyst_contract_diag_1.py"
ALLOWED = {
    PREFIX + name
    for name in ("__init__.py", "diagnose.py", "runner.py", "report.py", "cli.py")
} | {
    "examples/forgeai/evaluation/run_analyst_contract_diag_1.py",
    "examples/forgeai/" + TESTS,
    "planning/FORGEAI-ANALYST-CONTRACT-DIAGNOSTIC.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "validate_forgeai_analyst_contract_diag_1.py",
}
PROTECTED = ("src/", "packages/", "examples/forgeai/src/")
HISTORICAL = (
    "examples/forgeai/evaluation/analyst_quality1q/",
    "examples/forgeai/evaluation/content_discovery1/",
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY.md",
)
CHECKED = [
    "evaluation/analyst_contract_diag1",
    "evaluation/run_analyst_contract_diag_1.py",
    TESTS,
    str(ROOT / "validate_forgeai_analyst_contract_diag_1.py"),
]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, encoding="utf-8", check=True
    ).stdout


def changed() -> set[str]:
    paths = set(git("diff", "--name-only", BASE).splitlines())
    paths.update(
        git(
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            ".",
            ":(exclude)examples/forgeai/.lq13-test-temp/**",
        ).splitlines()
    )
    return paths


def scope() -> None:
    paths = changed()
    protected = sorted(p for p in paths if p.startswith(PROTECTED))
    if protected:
        raise RuntimeError("production source changed: " + repr(protected))
    if paths - ALLOWED:
        raise RuntimeError("unexpected scope: " + repr(sorted(paths - ALLOWED)))


def historical() -> None:
    touched = sorted(p for p in changed() if p.startswith(HISTORICAL))
    if touched:
        raise RuntimeError("historical 1Q/CD-1 evidence changed: " + repr(touched))


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(PYTHONDONTWRITEBYTECODE="1", UV_OFFLINE="1")
    phase = "1 scope guard / production non-interference"
    completed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="analyst-contract-diag-1-") as temporary:
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
                "--basetemp",
                str(temp / name.split()[0]),
                *(f"{TESTS}::{s}" for s in selectors),
            )

        def check(name: str, step: object) -> None:
            nonlocal phase
            phase = name
            print("[PHASE] " + name, flush=True)
            assert callable(step)
            step()
            completed.append(name)

        try:
            check(phase, scope)
            tests(
                "2 1Q frozen-input immutability",
                "test_historical_1q_inputs_and_classifier_unchanged",
            )
            tests(
                "3 Analyst source/prompt/parser unchanged",
                "test_contract_matches_the_unchanged_analyst",
            )
            tests(
                "4 diagnostic taxonomy",
                "test_taxonomy_is_closed_and_refines_the_1q_categories",
                "test_every_parser_stage_is_exercised",
            )
            tests(
                "5 first-failure ordering",
                "test_first_failure_stage_agrees_with_the_analyst",
            )
            tests(
                "6 field-set diagnostics",
                "test_field_set_diagnostics_and_canonical_missing_order",
            )
            tests(
                "7 canonical missing-field order",
                "test_field_set_diagnostics_and_canonical_missing_order",
            )
            tests(
                "8 no unexpected key names retained",
                "test_unexpected_field_names_are_never_retained",
            )
            tests(
                "9 required-field type classification",
                "test_required_field_types_are_closed",
            )
            tests(
                "10 ADR-021 representation classification",
                "test_representation_classification",
            )
            tests(
                "11 privacy",
                "test_report_privacy",
                "test_condition_links_the_frozen_1q_identity",
            )
            tests(
                "12 aggregate folding and pattern rule",
                "test_aggregate_folding_and_rendering",
                "test_pattern_rule",
            )
            tests(
                "13 report rendering and preflight refusal",
                "test_aggregate_folding_and_rendering",
                "test_live_preflight_refuses_without_writing",
            )
            check("14 historical 1Q report immutability", historical)
            run(
                "15 Analyst regressions",
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
                "tests/test_json_document.py",
            )
            run(
                "16 AuthorizedRepositoryEvidence regressions",
                ENGINEERING,
                "pytest",
                "-q",
                "-rs",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(temp / "evidence"),
                "tests/test_authorized_effects.py",
            )
            run(
                "17a DISCOVERY-1 regressions",
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
                "17b DISCOVERY-2A/2A.1, CONTENT-DISCOVERY-1 and 1Q regressions",
                FORGE,
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(temp / "discovery"),
                "evaluation/tests/test_discovery_2a.py",
                "evaluation/tests/test_discovery_2a1.py",
                "evaluation/tests/test_content_discovery_1.py",
                "evaluation/tests/test_analyst_quality_1q.py",
            )
            run(
                "18 ForgeAI architecture regressions",
                FORGE,
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_architecture.py",
                "evaluation/tests/test_lq1_architecture.py",
            )
            run("19 mypy", FORGE, "mypy", "--cache-dir", str(temp / "mypy"), *CHECKED)
            run("20 Ruff lint", FORGE, "ruff", "check", "--no-cache", *CHECKED)
            run(
                "21 Ruff format",
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *CHECKED,
            )
            phase = "22 git diff --check"
            subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
            completed.append(phase)
        except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
            for item in completed:
                print("PASS " + item)
            print(f"FAIL {phase}: {error}; later phases NOT RUN")
            return 1
    for item in completed:
        print("PASS " + item)
    print(
        "ANALYST-CONTRACT-DIAG-1 LOCAL VALIDATION PASSED - diagnostics harness only; "
        "no live model, no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
