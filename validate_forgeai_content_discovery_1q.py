r"""Offline CONTENT-DISCOVERY-1Q qualification. No live model, no Docker.

    uv run python .\validate_forgeai_content_discovery_1q.py

Qualifies the RepositoryAnalyst quality-measurement harness: scope and
production non-interference, frozen inputs, held-out fixtures and oracle,
thresholds, provenance, condition and report schemas, the Analyst request
boundary, the structural classifier, every metric, safety, privacy, replay,
folding and rendering, plus Analyst, evidence, DISCOVERY and ForgeAI
architecture regressions, mypy, Ruff and git diff --check.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENGINEERING = ROOT / "packages/legoai-engineering"
BASE = "ce3dfa787cabd68f5d64abac15864a7fe4698296"  # CONTENT-DISCOVERY-1
PREFIX = "examples/forgeai/evaluation/analyst_quality1q/"
TESTS = "evaluation/tests/test_analyst_quality_1q.py"
ALLOWED = {
    PREFIX + name
    for name in (
        "__init__.py",
        "data.py",
        "classify.py",
        "harness.py",
        "metrics.py",
        "report.py",
        "cli.py",
        "heldout-v1.json",
        "partition-v1.json",
        "thresholds-v1.json",
        "preregistration-v1.json",
        "manifest-v1.json",
    )
} | {
    "examples/forgeai/evaluation/run_analyst_quality_1q.py",
    "examples/forgeai/" + TESTS,
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "validate_forgeai_content_discovery_1q.py",
}
PROTECTED = ("src/", "packages/", "examples/forgeai/src/")
CHECKED = [
    "evaluation/analyst_quality1q",
    "evaluation/run_analyst_quality_1q.py",
    TESTS,
    str(ROOT / "validate_forgeai_content_discovery_1q.py"),
]


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
    protected = sorted(p for p in changed if p.startswith(PROTECTED))
    if protected:
        raise RuntimeError("production source changed: " + repr(protected))
    if changed - ALLOWED:
        raise RuntimeError("unexpected scope: " + repr(sorted(changed - ALLOWED)))


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(PYTHONDONTWRITEBYTECODE="1", UV_OFFLINE="1")
    phase = "1 scope guard / production non-interference"
    completed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="content-discovery-1q-") as temporary:
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

        try:
            print("[PHASE] " + phase, flush=True)
            scope()
            completed.append(phase)
            tests(
                "2 frozen CONTENT-DISCOVERY-1 immutability",
                "test_freeze_and_cd1_immutability",
            )
            tests("3 held-out quality fixture schema", "test_heldout_schema_and_oracle")
            tests(
                "4 oracle schema (held-out and derived CD-1 partition)",
                "test_heldout_schema_and_oracle",
                "test_cd1_partition_frozen",
            )
            tests(
                "5 threshold freeze",
                "test_thresholds_frozen",
                "test_freeze_and_cd1_immutability",
            )
            tests(
                "6 independence / provenance",
                "test_provenance_and_heldout_independence",
            )
            tests(
                "7 condition schema (written before the first call)",
                "test_condition_schema_and_plan",
                "test_condition_is_written_before_the_first_call",
            )
            tests("8 report schema", "test_report_schema")
            tests(
                "9 Analyst request boundary",
                "test_request_boundary_and_independent_repetitions",
            )
            tests(
                "10 output classifier", "test_output_classifier_agrees_with_the_analyst"
            )
            tests("11 relevant_files metrics", "test_relevance_metrics")
            tests("12 insufficient-evidence metrics", "test_insufficient_metrics")
            tests(
                "13 false-sufficient / catastrophic metrics",
                "test_false_sufficient_and_catastrophic",
            )
            tests(
                "14 safety invariants",
                "test_safety_invariants",
                "test_harness_is_evaluation_only",
            )
            tests("15 privacy", "test_report_privacy")
            tests(
                "16 replay / non-live harness and preflight refusals",
                "test_replay_harness_end_to_end",
                "test_preflight_refusals",
            )
            tests(
                "17 aggregate folding and decision rule",
                "test_aggregate_is_the_fold_of_the_records",
                "test_decision_rule_never_combines_b_and_c",
            )
            tests("18 report rendering", "test_report_rendering_and_no_overwrite")
            run(
                "19 Analyst regressions",
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
                "20 AuthorizedRepositoryEvidence regressions",
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
                "21a DISCOVERY-1 regressions",
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
                "21b DISCOVERY-2A/2A.1 and CONTENT-DISCOVERY-1 regressions",
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
            )
            run(
                "22 ForgeAI architecture regressions",
                FORGE,
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_architecture.py",
                "evaluation/tests/test_lq1_architecture.py",
            )
            run("23 mypy", FORGE, "mypy", "--cache-dir", str(temp / "mypy"), *CHECKED)
            run("24 Ruff lint", FORGE, "ruff", "check", "--no-cache", *CHECKED)
            run(
                "25 Ruff format",
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *CHECKED,
            )
            phase = "26 git diff --check"
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
        "CONTENT-DISCOVERY-1Q LOCAL VALIDATION PASSED - harness only; no live "
        "model, no Docker; Analyst quality not yet measured"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
