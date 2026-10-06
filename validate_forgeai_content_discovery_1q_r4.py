r"""Offline CONTENT-DISCOVERY-1Q-R4 qualification. No live model, no Docker.

uv run python .\validate_forgeai_content_discovery_1q_r4.py

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
BASE = "26b1c462aab6fd84590188a95042cb0328002047"  # 1.0.3 qualification recorded
EVALUATION = "examples/forgeai/evaluation/"
PACKAGE = EVALUATION + "analyst_quality1q_r4/"
TESTS = "evaluation/tests/test_analyst_quality_1q_r4.py"
ALLOWED = {
    PACKAGE + name
    for name in (
        "__init__.py",
        "data.py",
        "report.py",
        "cli.py",
        "preregistration-r4.json",
    )
} | {
    EVALUATION + "run_analyst_quality_1q_r4.py",
    "examples/forgeai/" + TESTS,
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R4.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "validate_forgeai_content_discovery_1q_r4.py",
}
PRODUCTION = ("src/", "packages/", "examples/forgeai/src/")
ORACLE = (
    EVALUATION + "analyst_quality1q/",
    EVALUATION + "content_discovery1/",
)
HISTORICAL_R3 = (
    EVALUATION + "analyst_quality1q_r3/",
    EVALUATION + "run_analyst_quality_1q_r3.py",
    EVALUATION + "tests/test_analyst_quality_1q_r3.py",
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R3.md",
)
HISTORICAL_COMPARE = (
    EVALUATION + "analyst_model_compare1/",
    EVALUATION + "run_analyst_model_compare_1.py",
    EVALUATION + "tests/test_analyst_model_compare_1.py",
    "planning/FORGEAI-ANALYST-MODEL-COMPARISON.md",
)
HISTORICAL_OTHER = (
    EVALUATION + "analyst_contract_diag1/",
    EVALUATION + "analyst_quality1q_r2/",
    EVALUATION + "analyst_insufficient_diag1/",
    "planning/FORGEAI-ANALYST-SUFFICIENCY-SEMANTICS-DECISION.md",
)
CHECKED = [
    "evaluation/analyst_quality1q_r4",
    "evaluation/run_analyst_quality_1q_r4.py",
    TESTS,
    str(ROOT / "validate_forgeai_content_discovery_1q_r4.py"),
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
            ":(exclude)**/aq1q-r3-*/**",
            ":(exclude)**/aq1q-r4-*/**",
            ":(exclude)**/amc1-*/**",
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
    phase = "1 scope guard"
    completed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="content-discovery-1q-r4-") as temporary:
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
            check("2 production non-interference", production)
            tests(
                "3 RepositoryAnalyst version 1.0.3",
                "test_analyst_identity_is_1_0_3",
            )
            tests("4 Analyst fingerprint pin", "test_fingerprint_pin")
            tests(
                "5 parser identity",
                "test_parser_identity_matches_prior_conditions",
            )
            tests(
                "6 ENG-ANALYST-SUFFICIENCY-SEMANTICS-1 qualification identity",
                "test_semantics_qualification_identity",
                "test_implementation_commit_must_be_an_ancestor",
            )
            check("7a R3 historical immutability", untouched(HISTORICAL_R3))
            tests(
                "7b R3 pinned to 1.0.2",
                "test_r3_history_is_unchanged_and_refuses_1_0_3",
            )
            check(
                "8a model-comparison historical immutability",
                untouched(HISTORICAL_COMPARE),
            )
            tests(
                "8b model comparison pinned to 1.0.2",
                "test_model_comparison_history_is_unchanged_and_refuses_1_0_3",
                "test_historical_references_are_recorded_not_recomputed",
            )
            check("8c other historical evidence unchanged", untouched(HISTORICAL_OTHER))
            tests(
                "9 frozen held-out fixtures",
                "test_frozen_heldout_fixtures_are_reused_by_digest",
                "test_tampered_oracle_partition_or_thresholds_refuse[heldout-v1.json]",
            )
            check("10a frozen held-out oracle files unchanged", untouched(ORACLE))
            tests("10b frozen held-out oracle", "test_heldout_oracle_is_unchanged")
            tests(
                "11 frozen partition",
                "test_partition_is_frozen",
                "test_tampered_oracle_partition_or_thresholds_refuse[partition-v1.json]",
            )
            tests(
                "12 frozen thresholds",
                "test_thresholds_are_frozen",
                "test_tampered_oracle_partition_or_thresholds_refuse[thresholds-v1.json]",
            )
            tests("13 call-plan identity", "test_call_plan")
            tests(
                "14 qwen2.5-coder:14b model/digest pin",
                "test_model_condition_is_the_committed_14b_pin",
            )
            tests(
                "15 frozen decision function",
                "test_decision_function_is_the_frozen_1q_rule",
            )
            tests("16 c15 unchanged", "test_c15_is_unchanged")
            tests(
                "17 c15 non-gating handling",
                "test_c15_never_affects_gates_or_decision",
                "test_known_conflict_must_be_a_non_gating_probe",
            )
            tests(
                "18 structural diagnostics", "test_structural_diagnostics_reuse_diag1"
            )
            tests(
                "19 insufficiency clause diagnostics",
                "test_insufficiency_clause_folding",
            )
            tests("20 answerable-success folding", "test_answerable_success_folding")
            tests("21 required-recall folding", "test_required_recall_folding")
            tests("22 acceptable-set folding", "test_acceptable_set_folding")
            tests(
                "23 insufficient-correctness folding",
                "test_insufficient_correctness_and_false_sufficient_folding",
            )
            tests(
                "24 false-sufficient folding",
                "test_insufficient_correctness_and_false_sufficient_folding",
            )
            tests(
                "25 q19-q22 per-case folding",
                "test_expected_insufficient_per_case_folding",
            )
            tests(
                "26 q11-q12 control folding",
                "test_future_behavior_control_folding",
            )
            tests("27 status confusion", "test_status_confusion")
            tests("28 standard safety metrics", "test_standard_safety_metrics")
            tests("29 report schema", "test_report_schema")
            tests("30 stop-rule mapping", "test_stop_rule_mapping")
            tests("31 deterministic reproduction", "test_deterministic_reproduction")
            tests("32 privacy/sentinel", "test_report_privacy")
            tests(
                "33 wrong Analyst refusal",
                "test_live_refuses_wrong_identity[wrong_analyst]",
                "test_wrong_analyst_identity_is_refused[version]",
                "test_wrong_analyst_identity_is_refused[source]",
            )
            tests(
                "34 wrong fingerprint refusal",
                "test_live_refuses_wrong_identity[wrong_fingerprint]",
                "test_wrong_analyst_identity_is_refused[fingerprint]",
            )
            tests(
                "35 parser mismatch refusal",
                "test_live_refuses_wrong_identity[parser_mismatch]",
                "test_wrong_analyst_identity_is_refused[parser]",
            )
            tests("36 dirty-tree refusal", "test_live_refuses_checkout_mismatch[dirty]")
            tests(
                "37 wrong branch/commit refusal",
                "test_live_refuses_checkout_mismatch[branch]",
                "test_live_refuses_checkout_mismatch[commit]",
            )
            tests(
                "38 wrong model/digest, unavailable model, unreachable Ollama refusal",
                "test_live_refuses_wrong_model_or_digest",
                "test_live_refuses_unreachable_ollama_or_unavailable_candidate",
            )
            tests(
                "39 placeholder hardware refusal",
                "test_live_refuses_placeholder_hardware",
            )
            tests(
                "40 existing output refusal",
                "test_live_refuses_existing_output",
                "test_harness_is_evaluation_only",
            )
            pytest(
                "41 Analyst regressions",
                ENGINEERING,
                "tests/test_analyst.py",
                "tests/test_analyst_architecture.py",
                "tests/test_analyst_prompt.py",
                "tests/test_analyst_sufficiency_prompt.py",
                "tests/test_json_document.py",
            )
            pytest(
                "42 AuthorizedRepositoryEvidence regressions",
                ENGINEERING,
                "tests/test_authorized_effects.py",
            )
            pytest(
                "43a DISCOVERY-1 regressions",
                ENGINEERING,
                "tests/test_structure.py",
                "tests/test_architecture.py",
            )
            pytest(
                "43b DISCOVERY-2A/2A.1, CONTENT-DISCOVERY-1, 1Q, DIAG-1, r2, "
                "insufficient diagnostic, R3 and model-comparison regressions",
                FORGE,
                "evaluation/tests/test_discovery_2a.py",
                "evaluation/tests/test_discovery_2a1.py",
                "evaluation/tests/test_content_discovery_1.py",
                "evaluation/tests/test_analyst_quality_1q.py",
                "evaluation/tests/test_analyst_contract_diag_1.py",
                "evaluation/tests/test_analyst_quality_1q_r2.py",
                "evaluation/tests/test_analyst_insufficient_diag_1.py",
                "evaluation/tests/test_analyst_quality_1q_r3.py",
                "evaluation/tests/test_analyst_model_compare_1.py",
            )
            pytest(
                "44 ForgeAI architecture regressions",
                FORGE,
                "tests/test_architecture.py",
                "evaluation/tests/test_lq1_architecture.py",
            )
            pytest(
                "45 Analyst 1.0.3 semantic regressions",
                ENGINEERING,
                "tests/test_analyst_sufficiency_semantics.py",
            )
            pytest("45b full R4 suite", FORGE, TESTS)
            run(
                "46 mypy",
                FORGE,
                "mypy",
                "--cache-dir",
                str(temp / "mypy"),
                *CHECKED,
            )
            run("47 Ruff lint", FORGE, "ruff", "check", "--no-cache", *CHECKED)
            run(
                "48 Ruff format",
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *CHECKED,
            )
            phase = "49 git diff --check"
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
        "CONTENT-DISCOVERY-1Q-R4 LOCAL VALIDATION PASSED - condition only; "
        "no live model, no Docker, no quality claim"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
