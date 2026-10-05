r"""Offline CONTENT-DISCOVERY-1Q-R3 qualification. No live model, no Docker.

uv run python .\validate_forgeai_content_discovery_1q_r3.py

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
BASE = "2dc417137a8ecb8e40cb2aed397246d9ad59a942"  # 1.0.2 qualification recorded
EVALUATION = "examples/forgeai/evaluation/"
PACKAGE = EVALUATION + "analyst_quality1q_r3/"
TESTS = "evaluation/tests/test_analyst_quality_1q_r3.py"
ALLOWED = {
    PACKAGE + name
    for name in (
        "__init__.py",
        "data.py",
        "runner.py",
        "report.py",
        "cli.py",
        "preregistration-r3.json",
    )
} | {
    EVALUATION + "run_analyst_quality_1q_r3.py",
    "examples/forgeai/" + TESTS,
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R3.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "validate_forgeai_content_discovery_1q_r3.py",
}
PRODUCTION = ("src/", "packages/", "examples/forgeai/src/")
HISTORICAL_1Q = (
    EVALUATION + "analyst_quality1q/",
    EVALUATION + "content_discovery1/",
    EVALUATION + "analyst_contract_diag1/",
    EVALUATION + "run_analyst_quality_1q.py",
    EVALUATION + "tests/test_analyst_quality_1q.py",
    EVALUATION + "tests/test_content_discovery_1.py",
    EVALUATION + "tests/test_analyst_contract_diag_1.py",
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY.md",
    "planning/FORGEAI-CONTENT-DISCOVERY-EVALUATION.md",
    "planning/FORGEAI-ANALYST-CONTRACT-DIAGNOSTIC.md",
)
HISTORICAL_R2 = (
    EVALUATION + "analyst_quality1q_r2/",
    EVALUATION + "run_analyst_quality_1q_r2.py",
    EVALUATION + "tests/test_analyst_quality_1q_r2.py",
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R2.md",
)
HISTORICAL_DIAG = (
    EVALUATION + "analyst_insufficient_diag1/",
    EVALUATION + "run_analyst_insufficient_diag_1.py",
    EVALUATION + "tests/test_analyst_insufficient_diag_1.py",
    "planning/FORGEAI-ANALYST-INSUFFICIENT-DIAGNOSTIC.md",
    "planning/FORGEAI-ANALYST-ABSTENTION-DECISION.md",
)
CHECKED = [
    "evaluation/analyst_quality1q_r3",
    "evaluation/run_analyst_quality_1q_r3.py",
    TESTS,
    str(ROOT / "validate_forgeai_content_discovery_1q_r3.py"),
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
    with tempfile.TemporaryDirectory(prefix="content-discovery-1q-r3-") as temporary:
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
                "3 Analyst version 1.0.2",
                "test_analyst_identity_is_pinned_to_1_0_2",
                "test_wrong_analyst_identity_is_refused[version_1_0_1]",
                "test_wrong_analyst_identity_is_refused[version_1_0_3]",
            )
            tests(
                "4 Analyst fingerprint pin",
                "test_wrong_analyst_identity_is_refused[fingerprint_1_0_1]",
                "test_wrong_analyst_identity_is_refused[fingerprint]",
                "test_wrong_analyst_identity_is_refused[source]",
            )
            tests(
                "5 parser identity pin",
                "test_parser_identity_is_unchanged_from_1_0_1",
                "test_wrong_analyst_identity_is_refused[parser]",
            )
            tests(
                "6 ENG-ANALYST-SUFFICIENCY-PROMPT-1 qualification identity",
                "test_sufficiency_prompt_qualification_identity",
                "test_implementation_commit_must_be_an_ancestor",
            )
            check("7a historical 1Q immutability", untouched(HISTORICAL_1Q))
            tests(
                "7b historical 1Q pinned",
                "test_historical_conditions_are_pinned_and_refuse_1_0_2",
            )
            check("8a historical r2 immutability", untouched(HISTORICAL_R2))
            pytest(
                "8b historical r2 suite (pinned 1.0.1)",
                FORGE,
                "evaluation/tests/test_analyst_quality_1q_r2.py",
            )
            check("9a historical DIAG-1 immutability", untouched(HISTORICAL_DIAG))
            pytest(
                "9b historical DIAG-1 suite (pinned 1.0.1)",
                FORGE,
                "evaluation/tests/test_analyst_insufficient_diag_1.py",
                TESTS + "::test_historical_references_are_recorded_not_recomputed",
            )
            tests("10 frozen fixture reuse", "test_frozen_inputs_are_reused_by_digest")
            pytest(
                "11 frozen oracle reuse",
                FORGE,
                TESTS + "::test_tampered_oracle_input_refuses",
                "evaluation/tests/test_analyst_quality_1q.py::"
                "test_heldout_schema_and_oracle",
            )
            tests("12 frozen partition reuse", "test_partition_and_call_plan")
            tests("13 frozen thresholds", "test_thresholds_are_frozen")
            tests("14 repetition/call-plan identity", "test_partition_and_call_plan")
            tests("15 model-condition identity", "test_model_condition_is_frozen")
            tests(
                "16 frozen decision-function identity",
                "test_decision_function_is_the_frozen_1q_rule",
            )
            tests(
                "17 structural diagnostic reuse",
                "test_structural_diagnostics_reuse_diag1",
            )
            tests(
                "18 clause diagnostic reuse",
                "test_clause_diagnostics_reuse_insufficient_diag1",
            )
            tests(
                "19 answerable-success folding",
                "test_answerable_and_abstention_folding",
                "test_replay_report_schema_and_reproduction",
            )
            tests("20 abstention folding", "test_answerable_and_abstention_folding")
            tests(
                "21 status confusion folding",
                "test_replay_report_schema_and_reproduction",
            )
            tests(
                "22 relevance metric folding",
                "test_relevance_and_safety_metrics_are_the_1q_functions",
                "test_replay_report_schema_and_reproduction",
            )
            tests(
                "23 safety metric folding",
                "test_relevance_and_safety_metrics_are_the_1q_functions",
                "test_harness_is_evaluation_only",
            )
            tests("24 report schema", "test_replay_report_schema_and_reproduction")
            tests(
                "25 deterministic reproduction",
                "test_replay_report_schema_and_reproduction",
            )
            tests("26 privacy", "test_report_privacy")
            tests(
                "27 wrong Analyst version refusal",
                "test_live_refuses_wrong_analyst[version]",
            )
            tests(
                "28 wrong fingerprint refusal",
                "test_live_refuses_wrong_analyst[fingerprint]",
            )
            tests("29 parser mismatch refusal", "test_live_refuses_parser_mismatch")
            tests("30 dirty-tree refusal", "test_live_refuses_checkout_mismatch[dirty]")
            tests(
                "31 wrong commit/branch refusal",
                "test_live_refuses_checkout_mismatch[commit]",
                "test_live_refuses_checkout_mismatch[branch]",
            )
            tests("32 wrong model/digest refusal", "test_live_refuses_wrong_model")
            tests(
                "33 hardware-placeholder refusal",
                "test_live_refuses_placeholder_hardware",
            )
            tests(
                "34 existing output refusal",
                "test_live_refuses_unreachable_ollama_and_existing_output",
            )
            pytest(
                "35 Analyst regressions",
                ENGINEERING,
                "tests/test_analyst.py",
                "tests/test_analyst_architecture.py",
                "tests/test_json_document.py",
            )
            pytest(
                "36 AuthorizedRepositoryEvidence regressions",
                ENGINEERING,
                "tests/test_authorized_effects.py",
            )
            pytest(
                "37a DISCOVERY-1 regressions",
                ENGINEERING,
                "tests/test_structure.py",
                "tests/test_architecture.py",
            )
            pytest(
                "37b DISCOVERY-2A/2A.1, CONTENT-DISCOVERY-1, 1Q and DIAG-1 regressions",
                FORGE,
                "evaluation/tests/test_discovery_2a.py",
                "evaluation/tests/test_discovery_2a1.py",
                "evaluation/tests/test_content_discovery_1.py",
                "evaluation/tests/test_analyst_quality_1q.py",
                "evaluation/tests/test_analyst_contract_diag_1.py",
            )
            pytest(
                "38 ForgeAI architecture regressions",
                FORGE,
                "tests/test_architecture.py",
                "evaluation/tests/test_lq1_architecture.py",
            )
            pytest(
                "39 Analyst 1.0.2 prompt regressions",
                ENGINEERING,
                "tests/test_analyst_sufficiency_prompt.py",
                "tests/test_analyst_prompt.py",
            )
            run("40 mypy", FORGE, "mypy", "--cache-dir", str(temp / "mypy"), *CHECKED)
            run("41 Ruff lint", FORGE, "ruff", "check", "--no-cache", *CHECKED)
            run(
                "42 Ruff format",
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *CHECKED,
            )
            phase = "43 git diff --check"
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
        "CONTENT-DISCOVERY-1Q-R3 LOCAL VALIDATION PASSED - condition harness only; "
        "no live model, no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
