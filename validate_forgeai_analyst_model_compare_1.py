r"""Offline ANALYST-MODEL-COMPARE-1 qualification. No live model, no pull, no Docker.

uv run python .\validate_forgeai_analyst_model_compare_1.py

Scope is pinned before this slice, so it works before and after committing.
Local run-output directories (never committed) are excluded from the scope scan.
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
BASE = "55f71a182bb4ddd4a1dbc25bebcc37b27f9aa732"  # R3 live result recorded
EVALUATION = "examples/forgeai/evaluation/"
PACKAGE = EVALUATION + "analyst_model_compare1/"
TESTS = "evaluation/tests/test_analyst_model_compare_1.py"
ALLOWED = {
    PACKAGE + name
    for name in (
        "__init__.py",
        "data.py",
        "report.py",
        "cli.py",
        "preregistration-compare1.json",
        "model-pins.json",
    )
} | {
    EVALUATION + "run_analyst_model_compare_1.py",
    "examples/forgeai/" + TESTS,
    "planning/FORGEAI-ANALYST-MODEL-COMPARISON.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "validate_forgeai_analyst_model_compare_1.py",
}
LOCAL_OUTPUTS = (
    ":(exclude)examples/forgeai/.lq13-test-temp/**",
    ":(exclude)examples/forgeai/aq1q-r3-qwen2.5-coder-7b/**",
    ":(exclude)examples/forgeai/amc1-*/**",
)
PRODUCTION = ("src/", "packages/", "examples/forgeai/src/")
R3_HISTORY = (
    EVALUATION + "analyst_quality1q_r3/",
    EVALUATION + "run_analyst_quality_1q_r3.py",
    EVALUATION + "tests/test_analyst_quality_1q_r3.py",
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R3.md",
    EVALUATION + "analyst_quality1q_r2/",
    EVALUATION + "analyst_insufficient_diag1/",
    EVALUATION + "analyst_quality1q/",
    EVALUATION + "analyst_contract_diag1/",
    EVALUATION + "content_discovery1/",
)
CHECKED = [
    "evaluation/analyst_model_compare1",
    "evaluation/run_analyst_model_compare_1.py",
    TESTS,
    str(ROOT / "validate_forgeai_analyst_model_compare_1.py"),
]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, encoding="utf-8", check=True
    ).stdout


def changed() -> set[str]:
    paths = set(git("diff", "--name-only", BASE).splitlines())
    paths.update(
        git(
            "ls-files", "--others", "--exclude-standard", "--", ".", *LOCAL_OUTPUTS
        ).splitlines()
    )
    return paths


def scope() -> None:
    paths = changed()
    if paths - ALLOWED:
        raise RuntimeError("unexpected scope: " + repr(sorted(paths - ALLOWED)))


def production() -> None:
    touched = sorted(p for p in changed() if p.startswith(PRODUCTION))
    if touched:
        raise RuntimeError("production source changed: " + repr(touched))


def r3_history() -> None:
    touched = sorted(p for p in changed() if p.startswith(R3_HISTORY))
    if touched:
        raise RuntimeError("historical evidence changed: " + repr(touched))


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(PYTHONDONTWRITEBYTECODE="1", UV_OFFLINE="1")
    phase = "1 scope guard"
    completed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="analyst-model-compare-1-") as temporary:
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

        rule = "test_comparison_rule"
        try:
            check(phase, scope)
            check("2 production non-interference", production)
            tests("3 Analyst 1.0.2 unchanged", "test_analyst_identity_is_the_r3_1_0_2")
            tests(
                "4 Analyst fingerprint pin",
                "test_analyst_identity_is_the_r3_1_0_2",
                "test_refuses_wrong_analyst",
            )
            tests("5 parser identity pin", "test_parser_identity_pin")
            check("6a R3 historical immutability", r3_history)
            tests("6b R3 history references", "test_r3_history_is_unchanged")
            tests(
                "7 workload digest reuse",
                "test_workload_oracle_threshold_and_plan_reuse",
            )
            pytest(
                "8 oracle reuse",
                FORGE,
                TESTS + "::test_workload_oracle_threshold_and_plan_reuse",
                "evaluation/tests/test_analyst_quality_1q.py::"
                "test_heldout_schema_and_oracle",
            )
            tests(
                "9 threshold reuse",
                "test_workload_oracle_threshold_and_plan_reuse",
                "test_margins_are_preregistered",
            )
            tests("10 call-plan reuse", "test_workload_oracle_threshold_and_plan_reuse")
            tests("11 decision-rule reuse", "test_decision_rule_reuse")
            tests("12 control metrics pin", "test_control_metrics_pin")
            tests(
                "13 candidate-condition schema",
                "test_per_model_report_isolation",
                "test_candidate_registry_and_pins",
            )
            tests("14 comparison-report schema", "test_compare_command_end_to_end")
            tests(
                "15 model identity/digest enforcement",
                "test_candidate_registry_and_pins",
                "test_pin_file_format",
                "test_candidate_identity_verification",
            )
            tests(
                "16 hardware identity",
                "test_refuses_placeholder_hardware_and_unreachable_ollama",
            )
            tests(
                "17 smoke-not-quality semantics", "test_smoke_is_not_quality_evidence"
            )
            tests("18 full-run no early stop", "test_full_run_has_no_early_stop")
            tests("19 per-model report isolation", "test_per_model_report_isolation")
            tests(
                "20 comparison aggregation",
                "test_compare_command_end_to_end",
                "test_comparison_d_and_c_outcomes",
                f"{rule}[all_gates]",
                f"{rule}[material]",
                f"{rule}[within_noise]",
            )
            tests(
                "21 false-sufficient comparison", f"{rule}[false_sufficient_priority]"
            )
            tests(
                "22 recall comparison",
                f"{rule}[recall_priority]",
                f"{rule}[class_inconsistency]",
            )
            tests("23 structural validity comparison", f"{rule}[validity_tradeoff]")
            tests("24 safety comparison", f"{rule}[safety_blocks]")
            tests("25 privacy", "test_report_privacy")
            tests("26 wrong Analyst refusal", "test_refuses_wrong_analyst")
            tests("27 wrong model/digest refusal", "test_refuses_wrong_model_or_digest")
            tests("28 dirty-tree refusal", "test_refuses_checkout_mismatch[dirty]")
            tests(
                "29 wrong branch/commit refusal",
                "test_refuses_checkout_mismatch[branch]",
                "test_refuses_checkout_mismatch[commit]",
            )
            tests(
                "30 output collision refusal",
                "test_refuses_output_collision",
                "test_harness_is_evaluation_only",
            )
            pytest(
                "31 R3 regressions",
                FORGE,
                "evaluation/tests/test_analyst_quality_1q_r3.py",
            )
            pytest(
                "32 Analyst regressions",
                ENGINEERING,
                "tests/test_analyst.py",
                "tests/test_analyst_architecture.py",
                "tests/test_json_document.py",
                "tests/test_analyst_sufficiency_prompt.py",
            )
            pytest(
                "33 AuthorizedRepositoryEvidence regressions",
                ENGINEERING,
                "tests/test_authorized_effects.py",
            )
            pytest(
                "34a DISCOVERY-1 regressions",
                ENGINEERING,
                "tests/test_structure.py",
                "tests/test_architecture.py",
            )
            pytest(
                "34b DISCOVERY-2A/2A.1, CONTENT-DISCOVERY-1, 1Q, DIAG-1, r2 and "
                "insufficient-diagnostic regressions",
                FORGE,
                "evaluation/tests/test_discovery_2a.py",
                "evaluation/tests/test_discovery_2a1.py",
                "evaluation/tests/test_content_discovery_1.py",
                "evaluation/tests/test_analyst_quality_1q.py",
                "evaluation/tests/test_analyst_contract_diag_1.py",
                "evaluation/tests/test_analyst_quality_1q_r2.py",
                "evaluation/tests/test_analyst_insufficient_diag_1.py",
            )
            pytest(
                "35 ForgeAI architecture regressions",
                FORGE,
                "tests/test_architecture.py",
                "evaluation/tests/test_lq1_architecture.py",
            )
            run("36 mypy", FORGE, "mypy", "--cache-dir", str(temp / "mypy"), *CHECKED)
            run("37 Ruff lint", FORGE, "ruff", "check", "--no-cache", *CHECKED)
            run(
                "38 Ruff format",
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *CHECKED,
            )
            phase = "39 git diff --check"
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
        "ANALYST-MODEL-COMPARE-1 LOCAL VALIDATION PASSED - comparison harness only; "
        "no live model, no model pull, no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
