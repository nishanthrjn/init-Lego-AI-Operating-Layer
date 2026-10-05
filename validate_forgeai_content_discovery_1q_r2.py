r"""Offline CONTENT-DISCOVERY-1Q-R2 qualification. No live model, no Docker.

uv run python .\validate_forgeai_content_discovery_1q_r2.py

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
BASE = "24ead5e3d4ac4cf84dcfa95793990df905245c28"  # ENG-ANALYST-PROMPT-1 recorded
EVALUATION = "examples/forgeai/evaluation/"
PACKAGE = EVALUATION + "analyst_quality1q_r2/"
TESTS = "evaluation/tests/test_analyst_quality_1q_r2.py"
ALLOWED = {
    PACKAGE + name
    for name in (
        "__init__.py",
        "data.py",
        "runner.py",
        "report.py",
        "cli.py",
        "preregistration-r2.json",
    )
} | {
    EVALUATION + "run_analyst_quality_1q_r2.py",
    "examples/forgeai/" + TESTS,
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R2.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "validate_forgeai_content_discovery_1q_r2.py",
}
PRODUCTION = ("src/", "packages/", "examples/forgeai/src/")
HISTORICAL_1Q = (
    EVALUATION + "analyst_quality1q/",
    EVALUATION + "content_discovery1/",
    EVALUATION + "run_analyst_quality_1q.py",
    EVALUATION + "tests/test_analyst_quality_1q.py",
    EVALUATION + "tests/test_content_discovery_1.py",
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY.md",
    "planning/FORGEAI-CONTENT-DISCOVERY-EVALUATION.md",
)
HISTORICAL_DIAG = (
    EVALUATION + "analyst_contract_diag1/",
    EVALUATION + "run_analyst_contract_diag_1.py",
    EVALUATION + "tests/test_analyst_contract_diag_1.py",
    "planning/FORGEAI-ANALYST-CONTRACT-DIAGNOSTIC.md",
)
CHECKED = [
    "evaluation/analyst_quality1q_r2",
    "evaluation/run_analyst_quality_1q_r2.py",
    TESTS,
    str(ROOT / "validate_forgeai_content_discovery_1q_r2.py"),
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
    with tempfile.TemporaryDirectory(prefix="content-discovery-1q-r2-") as temporary:
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
            check("2a historical 1Q/CD-1 immutability", untouched(HISTORICAL_1Q))
            tests(
                "2b historical 1Q pinned to 1.0.0",
                "test_historical_1q_and_cd1_are_unchanged_and_pinned_to_1_0_0",
                "test_1q_live_command_refuses_analyst_1_0_1",
            )
            check("3a historical DIAG-1 immutability", untouched(HISTORICAL_DIAG))
            tests(
                "3b historical DIAG-1 referenced, not recomputed",
                "test_historical_diag1_identity_is_referenced_not_recomputed",
            )
            tests(
                "4 RepositoryAnalyst version 1.0.1",
                "test_analyst_identity_is_pinned_to_1_0_1",
                "test_wrong_analyst_identity_is_refused[version_1_0_2]",
                "test_wrong_analyst_identity_is_refused[version_1_0_0]",
            )
            tests(
                "5 Analyst fingerprint pin",
                "test_analyst_identity_is_pinned_to_1_0_1",
                "test_wrong_analyst_identity_is_refused[fingerprint]",
                "test_wrong_analyst_identity_is_refused[fingerprint_1_0_0]",
                "test_wrong_analyst_identity_is_refused[source]",
                "test_implementation_commit_must_be_an_ancestor",
            )
            tests(
                "6 parser/schema unchanged",
                "test_parser_and_schema_are_unchanged_from_1_0_0",
            )
            tests(
                "7 frozen fixture reuse",
                "test_frozen_inputs_are_reused_by_digest",
                "test_tampered_1q_input_refuses",
            )
            pytest(
                "8 frozen oracle reuse",
                FORGE,
                TESTS + "::test_frozen_inputs_are_reused_by_digest",
                "evaluation/tests/test_analyst_quality_1q.py::"
                "test_heldout_schema_and_oracle",
            )
            tests(
                "9 frozen threshold reuse",
                "test_thresholds_and_model_condition_are_unchanged",
            )
            tests("10 partition reuse", "test_partition_repetitions_and_call_count")
            tests(
                "11 call-count/repetition identity",
                "test_partition_repetitions_and_call_count",
            )
            tests(
                "12 model-condition identity",
                "test_thresholds_and_model_condition_are_unchanged",
            )
            tests(
                "13 structural diagnostics",
                "test_structural_diagnosis_reuses_diag1_on_the_same_call",
            )
            tests(
                "14 relevance metric identity",
                "test_quality_metrics_and_safety_are_the_1q_functions",
            )
            tests(
                "15 safety metric identity",
                "test_quality_metrics_and_safety_are_the_1q_functions",
                "test_harness_is_evaluation_only",
            )
            tests(
                "16 decision-rule identity", "test_decision_rule_is_the_frozen_1q_rule"
            )
            tests("17 report schema", "test_replay_report_schema_and_folding")
            tests(
                "18 folding/reproduction",
                "test_replay_report_schema_and_folding",
                "test_historical_comparison_observation",
            )
            tests("19 privacy", "test_report_privacy")
            tests(
                "20 wrong-version refusal",
                "test_live_refuses_wrong_analyst[version]",
            )
            tests(
                "21 wrong-fingerprint refusal",
                "test_live_refuses_wrong_analyst[fingerprint]",
            )
            tests("22 dirty-tree refusal", "test_live_refuses_checkout_mismatch[dirty]")
            tests(
                "23 commit mismatch refusal",
                "test_live_refuses_checkout_mismatch[commit]",
                "test_live_refuses_checkout_mismatch[branch]",
            )
            tests(
                "24 model digest refusal",
                "test_live_refuses_model_digest_mismatch_before_ollama",
            )
            tests(
                "25 output-directory refusal",
                "test_live_refuses_unreachable_ollama_and_existing_output",
            )
            pytest(
                "26 Analyst regressions",
                ENGINEERING,
                "tests/test_analyst.py",
                "tests/test_analyst_architecture.py",
                "tests/test_json_document.py",
            )
            pytest(
                "27 AuthorizedRepositoryEvidence regressions",
                ENGINEERING,
                "tests/test_authorized_effects.py",
            )
            pytest(
                "28a DISCOVERY-1 regressions",
                ENGINEERING,
                "tests/test_structure.py",
                "tests/test_architecture.py",
            )
            pytest(
                "28b DISCOVERY-2A/2A.1, CONTENT-DISCOVERY-1, 1Q and DIAG-1 regressions",
                FORGE,
                "evaluation/tests/test_discovery_2a.py",
                "evaluation/tests/test_discovery_2a1.py",
                "evaluation/tests/test_content_discovery_1.py",
                "evaluation/tests/test_analyst_quality_1q.py",
                "evaluation/tests/test_analyst_contract_diag_1.py",
            )
            pytest(
                "29 ForgeAI architecture regressions",
                FORGE,
                "tests/test_architecture.py",
                "evaluation/tests/test_lq1_architecture.py",
            )
            pytest(
                "30 ENG-ANALYST-PROMPT-1 regressions",
                ENGINEERING,
                "tests/test_analyst_prompt.py",
            )
            run("31 mypy", FORGE, "mypy", "--cache-dir", str(temp / "mypy"), *CHECKED)
            run("32 Ruff lint", FORGE, "ruff", "check", "--no-cache", *CHECKED)
            run(
                "33 Ruff format",
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *CHECKED,
            )
            phase = "34 git diff --check"
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
        "CONTENT-DISCOVERY-1Q-R2 LOCAL VALIDATION PASSED - condition harness only; "
        "no live model, no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
