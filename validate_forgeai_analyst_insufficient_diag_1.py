r"""Offline ANALYST-INSUFFICIENT-DIAG-1 qualification. No live model, no Docker.

uv run python .\validate_forgeai_analyst_insufficient_diag_1.py

Scope is pinned before this slice, so it works before and after committing.
"""

import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENGINEERING = ROOT / "packages/legoai-engineering"
BASE = "02cf734980da8c4dccb5913f34462886dd66cefb"  # 1Q-R2 live result recorded
EVALUATION = "examples/forgeai/evaluation/"
PACKAGE = EVALUATION + "analyst_insufficient_diag1/"
TESTS = "evaluation/tests/test_analyst_insufficient_diag_1.py"
ALLOWED = {
    PACKAGE + name
    for name in ("__init__.py", "clauses.py", "runner.py", "report.py", "cli.py")
} | {
    EVALUATION + "run_analyst_insufficient_diag_1.py",
    "examples/forgeai/" + TESTS,
    "planning/FORGEAI-ANALYST-INSUFFICIENT-DIAGNOSTIC.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "validate_forgeai_analyst_insufficient_diag_1.py",
}
PRODUCTION = ("src/", "packages/", "examples/forgeai/src/")
HISTORICAL_R2 = (
    EVALUATION + "analyst_quality1q_r2/",
    EVALUATION + "run_analyst_quality_1q_r2.py",
    EVALUATION + "tests/test_analyst_quality_1q_r2.py",
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R2.md",
)
HISTORICAL_1Q_DIAG = (
    EVALUATION + "analyst_quality1q/",
    EVALUATION + "content_discovery1/",
    EVALUATION + "analyst_contract_diag1/",
    EVALUATION + "run_analyst_quality_1q.py",
    EVALUATION + "run_analyst_contract_diag_1.py",
    EVALUATION + "tests/test_analyst_quality_1q.py",
    EVALUATION + "tests/test_analyst_contract_diag_1.py",
    EVALUATION + "tests/test_content_discovery_1.py",
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY.md",
    "planning/FORGEAI-CONTENT-DISCOVERY-EVALUATION.md",
    "planning/FORGEAI-ANALYST-CONTRACT-DIAGNOSTIC.md",
)
CHECKED = [
    "evaluation/analyst_insufficient_diag1",
    "evaluation/run_analyst_insufficient_diag_1.py",
    TESTS,
    str(ROOT / "validate_forgeai_analyst_insufficient_diag_1.py"),
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
    production = sorted(p for p in paths if p.startswith(PRODUCTION))
    if production:
        raise RuntimeError("production source changed: " + repr(production))
    if paths - ALLOWED:
        raise RuntimeError("unexpected scope: " + repr(sorted(paths - ALLOWED)))


def untouched(prefixes: tuple[str, ...]) -> Callable[[], None]:
    def step() -> None:
        touched = sorted(p for p in changed() if p.startswith(prefixes))
        if touched:
            raise RuntimeError("historical evidence changed: " + repr(touched))

    return step


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(PYTHONDONTWRITEBYTECODE="1", UV_OFFLINE="1")
    phase = "1 scope guard / production non-interference"
    completed: list[str] = []
    with tempfile.TemporaryDirectory(
        prefix="analyst-insufficient-diag-1-"
    ) as temporary:
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

        def pytest(name: str, cwd: Path, *targets: str) -> None:
            run(
                name,
                cwd,
                "pytest",
                "-q",
                "-rs",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(temp / name.split()[0]),
                *targets,
            )

        def tests(name: str, *selectors: str) -> None:
            pytest(name, FORGE, *(f"{TESTS}::{s}" for s in selectors))

        def check(name: str, step: Callable[[], None]) -> None:
            nonlocal phase
            phase = name
            print("[PHASE] " + name, flush=True)
            step()
            completed.append(name)

        try:
            check(phase, scope)
            check("2a r2 historical immutability", untouched(HISTORICAL_R2))
            tests("2b r2 identity linkage", "test_linkage_is_the_recorded_r2_identity")
            tests(
                "3 Analyst 1.0.1 unchanged",
                "test_analyst_and_r2_condition_are_unchanged",
            )
            pytest(
                "4 parser/rule unchanged",
                FORGE,
                TESTS + "::test_analyst_and_r2_condition_are_unchanged",
                "evaluation/tests/test_analyst_quality_1q_r2.py::"
                "test_parser_and_schema_are_unchanged_from_1_0_0",
            )
            tests("5 refined taxonomy", "test_refinement_mirrors_the_unchanged_rule")
            tests(
                "6 first-failure ordering",
                "test_first_failure_ordering_is_preserved",
                "test_insufficient_rule_precedes_membership",
                "test_observe_takes_counts_only_after_the_rule_is_reached",
            )
            tests(
                "7 findings-count classification",
                "test_insufficient_clauses_agree_with_the_analyst[findings]",
            )
            tests(
                "8 unknowns-count classification",
                "test_insufficient_clauses_agree_with_the_analyst[unknowns]",
            )
            tests(
                "9 both-clause classification",
                "test_insufficient_clauses_agree_with_the_analyst[both]",
            )
            tests(
                "10 expected-outcome linkage",
                "test_expected_outcome_and_actual_status_linkage",
            )
            tests(
                "11 actual-status classification",
                "test_expected_outcome_and_actual_status_linkage",
                "test_records_extend_the_r2_record_for_the_same_reply",
            )
            tests(
                "12 confusion-matrix folding",
                "test_confusion_and_abstention_fold_exactly",
            )
            tests(
                "13 valid-vs-invalid abstention separation",
                "test_valid_abstention_and_valid_success_are_separate",
                "test_from_r2_maps_recorded_records",
                "test_recorded_mode_cannot_select_a_without_clauses",
            )
            tests("14 privacy", "test_report_privacy")
            tests(
                "15 report schema",
                "test_replay_report_schema_and_deterministic_folding",
                "test_recorded_mode_requires_the_exact_r2_report",
            )
            tests(
                "16 deterministic aggregation and decision rule",
                "test_replay_report_schema_and_deterministic_folding",
                "test_next_decision_rule",
                "test_live_refuses_a_different_analyst",
                "test_live_refuses_model_checkout_and_existing_output",
                "test_harness_is_evaluation_only",
            )
            check("17 historical 1Q/DIAG-1 immutability", untouched(HISTORICAL_1Q_DIAG))
            pytest(
                "18 Analyst regressions",
                ENGINEERING,
                "tests/test_analyst.py",
                "tests/test_analyst_architecture.py",
                "tests/test_json_document.py",
            )
            pytest(
                "19 AuthorizedRepositoryEvidence regressions",
                ENGINEERING,
                "tests/test_authorized_effects.py",
            )
            pytest(
                "20a DISCOVERY-1 regressions",
                ENGINEERING,
                "tests/test_structure.py",
                "tests/test_architecture.py",
            )
            pytest(
                "20b DISCOVERY-2A/2A.1, CONTENT-DISCOVERY-1, 1Q and DIAG-1 regressions",
                FORGE,
                "evaluation/tests/test_discovery_2a.py",
                "evaluation/tests/test_discovery_2a1.py",
                "evaluation/tests/test_content_discovery_1.py",
                "evaluation/tests/test_analyst_quality_1q.py",
                "evaluation/tests/test_analyst_contract_diag_1.py",
            )
            pytest(
                "21 ForgeAI architecture regressions",
                FORGE,
                "tests/test_architecture.py",
                "evaluation/tests/test_lq1_architecture.py",
            )
            pytest(
                "22 ENG-ANALYST-PROMPT-1 regressions",
                ENGINEERING,
                "tests/test_analyst_prompt.py",
            )
            pytest(
                "23 1Q-R2 regressions",
                FORGE,
                "evaluation/tests/test_analyst_quality_1q_r2.py",
            )
            run("24 mypy", FORGE, "mypy", "--cache-dir", str(temp / "mypy"), *CHECKED)
            run("25 Ruff lint", FORGE, "ruff", "check", "--no-cache", *CHECKED)
            run(
                "26 Ruff format",
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *CHECKED,
            )
            phase = "27 git diff --check"
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
        "ANALYST-INSUFFICIENT-DIAG-1 LOCAL VALIDATION PASSED - diagnostic harness only; "
        "no live model, no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
