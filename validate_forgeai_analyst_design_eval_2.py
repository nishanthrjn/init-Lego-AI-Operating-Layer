r"""Offline operator qualification: uv run python .\validate_forgeai_analyst_design_eval_2.py."""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENG = ROOT / "packages/legoai-engineering"
BASE = "dcafc5e0434c5d3aee56488a279ae71afe99119a"
SELF = "validate_forgeai_analyst_design_eval_2.py"
TEST = "evaluation/tests/test_analyst_design_eval2.py"
PACKAGE = "evaluation/analyst_design_eval2"
DECISION = "planning/FORGEAI-ANALYST-DESIGN-REASSESSMENT.md"
ALLOWED = {
    SELF,
    DECISION,
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "examples/forgeai/" + TEST,
} | {
    "examples/forgeai/" + PACKAGE + "/" + name
    for name in (
        "__init__.py",
        "data.py",
        "inputs.py",
        "requests.py",
        "runner.py",
        "metrics.py",
        "report.py",
        "README.md",
        "fixtures-v2.json",
        "oracle-v2.json",
        "gates-v2.json",
        "schema-v2.json",
        "freeze-v2.json",
        "CASES.md",
        "inputs-v2.json",
        "inventory-v2.json",
        "set-controls-v2.json",
    )
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
            "--exclude=examples/forgeai/.lq13-test-temp/",
            "--",
            "src",
            "packages",
            "examples",
            "planning",
            "docs",
            SELF,
        ).splitlines()
    )
    if changed - ALLOWED:
        raise RuntimeError(
            "unexpected changed files: " + repr(sorted(changed - ALLOWED))
        )
    before = git("show", f"{BASE}:{DECISION}").replace("\r\n", "\n")
    if not (ROOT / DECISION).read_text(encoding="utf-8").startswith(before):
        raise RuntimeError("reassessment must remain append-only")


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(UV_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    completed: list[str] = []
    phase = "initialization"
    with tempfile.TemporaryDirectory(prefix="analyst-design-") as directory:
        temp = Path(directory)
        env["UV_CACHE_DIR"] = str(temp / "uv-cache")

        def start(name: str) -> None:
            nonlocal phase
            phase = name
            print("[PHASE] " + name, flush=True)

        def run(name: str, cwd: Path, *args: str) -> None:
            start(name)
            subprocess.run(
                ["uv", "run", "--locked", "--no-sync", "python", "-B", "-m", *args],
                cwd=cwd,
                env=env,
                check=True,
            )
            completed.append(name)

        def tests(name: str, cwd: Path, *targets: str) -> None:
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

        try:
            start("1 revision-1 and production unchanged")
            scope()
            for protected in (
                "src",
                "packages",
                "adrs",
                "examples/forgeai/src",
                "examples/forgeai/evaluation/analyst_design_eval1",
                "examples/forgeai/evaluation/analyst_evidence_loop",
                "examples/forgeai/evaluation/tests/test_analyst_design_eval.py",
                "examples/forgeai/evaluation/analyst_quality1q_r3",
                "examples/forgeai/evaluation/analyst_quality1q_r4",
            ):
                if git("diff", "--name-only", BASE, "--", protected):
                    raise RuntimeError(
                        "protected history/production changed: " + protected
                    )
            completed.append(phase)
            start("2 revision-1 digests unchanged")
            if git(
                "diff",
                "--name-only",
                BASE,
                "--",
                "examples/forgeai/evaluation/analyst_design_eval1",
            ):
                raise RuntimeError("revision-1 changed")
            completed.append(phase)
            tests(
                "3 revision-1 and R3/R4 qualification regressions",
                FORGE,
                "evaluation/tests/test_analyst_design_eval.py",
                "evaluation/tests/test_analyst_quality_1q_r3.py",
                "evaluation/tests/test_analyst_quality_1q_r4.py",
            )
            report = temp / "design.xml"
            tests(
                "4 condition identities and complete evaluator suite",
                FORGE,
                TEST,
                f"--junitxml={report}",
            )
            cases = list(ET.parse(report).getroot().iter("testcase"))
            if not cases or any(list(c) for c in cases):
                raise RuntimeError("suite must pass without skips/failures")
            names = {c.attrib["name"].split("[")[0] for c in cases}
            coverage = [
                (
                    "5 distinct fixture identity",
                    "frozen_identity_membership_and_live_gates",
                ),
                (
                    "6 distinct oracle identity",
                    "frozen_identity_membership_and_live_gates",
                ),
                (
                    "7 distinct schema identity",
                    "frozen_identity_membership_and_live_gates",
                ),
                (
                    "8 distinct gate identity",
                    "frozen_identity_membership_and_live_gates",
                ),
                (
                    "9 initial manifests oracle-independent",
                    "oracle_changes_cannot_construct_input",
                ),
                (
                    "10 ambiguity no clarification leak",
                    "governed_initial_payload_and_provenance_inventory",
                ),
                (
                    "11 missing-evidence no request leak",
                    "governed_initial_payload_and_provenance_inventory",
                ),
                (
                    "12 no hidden path leak",
                    "governed_initial_payload_and_provenance_inventory",
                ),
                (
                    "13 no disposition leak",
                    "governed_initial_payload_and_provenance_inventory",
                ),
                (
                    "14 model USER payload inspected",
                    "governed_initial_payload_and_provenance_inventory",
                ),
                (
                    "15 complete request-set retained",
                    "complete_record_roundtrip_preserves_order_and_choices",
                ),
                ("16 zero-request scoring", "complete_sets"),
                ("17 one-request scoring", "complete_sets"),
                ("18 multi-request scoring", "complete_sets"),
                ("19 mixed evidence and clarification", "complete_sets"),
                ("20 required recall", "complete_sets"),
                ("21 precision", "complete_sets"),
                ("22 allowed extras", "complete_sets"),
                ("23 forbidden extras", "complete_sets"),
                (
                    "24 semantic duplicates",
                    "matching_alternatives_choices_paths_and_semantic_duplicates",
                ),
                ("25 invented paths", "complete_sets"),
                (
                    "26 source roles",
                    "matching_alternatives_choices_paths_and_semantic_duplicates",
                ),
                (
                    "27 clarification matching",
                    "matching_alternatives_choices_paths_and_semantic_duplicates",
                ),
                (
                    "28 named matching",
                    "matching_alternatives_choices_paths_and_semantic_duplicates",
                ),
                (
                    "29 false-sufficient gate",
                    "false_progression_and_invalid_denominators",
                ),
                ("30 over-requesting", "complete_sets"),
                ("31 under-requesting", "complete_sets"),
                ("32 authority separate", "semantic_errors_and_authority_are_separate"),
                (
                    "33 one-round mixed stop",
                    "mixed_one_round_profile_stops_without_executing_both",
                ),
                ("34 acquisition pairs", "pairs_and_bounded_intervention"),
                ("35 clarification pairs", "pairs_and_bounded_intervention"),
                ("36 unrelated pairs", "pairs_and_bounded_intervention"),
                ("37 future behavior", "multistep_deltas_future_and_malicious"),
                ("38 malicious content", "multistep_deltas_future_and_malicious"),
                (
                    "39 operational controls",
                    "reference_metrics_and_operational_controls",
                ),
                (
                    "40 q19-q22 nongating",
                    "operator_repair_and_regressions_not_independent_credit",
                ),
                (
                    "41 repair not independent credit",
                    "operator_repair_and_regressions_not_independent_credit",
                ),
                (
                    "42 first-request mutation",
                    "request_scorer_mutants_fail_golden_assertions",
                ),
                (
                    "43 ignored-extra mutation",
                    "request_scorer_mutants_fail_golden_assertions",
                ),
                (
                    "44 any-correct mutation",
                    "request_scorer_mutants_fail_golden_assertions",
                ),
                (
                    "45 mixed-invalid mutation",
                    "request_scorer_mutants_fail_golden_assertions",
                ),
                ("46 request-leak mutation", "payload_leak_mutants_rejected"),
                ("47 path-leak mutation", "payload_leak_mutants_rejected"),
                (
                    "48 unresolved-mixed progression mutation",
                    "progression_and_repair_scorer_mutants",
                ),
                ("49 freeze guard", "freeze_mutation_guard"),
                ("50 live N unauthorized", "frozen_identity_membership_and_live_gates"),
                (
                    "51 live final-analysis unauthorized",
                    "frozen_identity_membership_and_live_gates",
                ),
            ]
            for name, case in coverage:
                start(name)
                if "test_" + case not in names:
                    raise RuntimeError("missing passing case: " + case)
                print("  verified in phase 4: " + case)
                completed.append(name)
            tests(
                "52 sufficiency Agent regressions",
                ENG,
                "tests/test_sufficiency_agent.py",
            )
            tests(
                "53 evidence-loop regressions",
                FORGE,
                "evaluation/tests/test_analyst_evidence_loop.py",
            )
            start("54 revision-1 regression preservation")
            if "3 revision-1 and R3/R4 qualification regressions" not in completed:
                raise RuntimeError("revision-1 regressions missing")
            completed.append(phase)
            tests(
                "55 RepositoryAnalyst regressions",
                ENG,
                "tests/test_analyst.py",
                "tests/test_json_document.py",
                "tests/test_analyst_prompt.py",
                "tests/test_analyst_sufficiency_prompt.py",
                "tests/test_analyst_sufficiency_semantics.py",
            )
            tests(
                "56 M7 regressions",
                ROOT,
                "tests/unit/execution/test_agent.py",
                "tests/integration/composition/test_agent.py",
                "tests/architecture/test_agent.py",
            )
            tests(
                "57 ForgeAI worker regressions",
                FORGE,
                "tests/test_worker.py",
                "tests/test_architecture.py",
            )
            tests(
                "58 architecture/import guards",
                ENG,
                "tests/test_architecture.py",
                "tests/test_analyst_architecture.py",
            )
            start("59 no live/provider calls")
            if "test_architecture_inputs_have_no_oracle_or_effects" not in names:
                raise RuntimeError("boundary guard missing")
            completed.append(phase)
            checked = [PACKAGE, TEST, str(ROOT / SELF)]
            run("60 mypy", FORGE, "mypy", "--cache-dir", str(temp / "mypy"), *checked)
            run("61 Ruff lint", FORGE, "ruff", "check", "--no-cache", *checked)
            run(
                "62 Ruff format",
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *checked,
            )
            start("63 git diff check")
            subprocess.run(["git", "diff", "--check", BASE], cwd=ROOT, check=True)
            for name in ALLOWED:
                text = (ROOT / name).read_text(encoding="utf-8")
                if text.endswith("\n\n") or any(
                    line.rstrip() != line for line in text.splitlines()
                ):
                    raise RuntimeError("new-file whitespace error: " + name)
            completed.append(phase)
        except (
            OSError,
            ValueError,
            RuntimeError,
            subprocess.CalledProcessError,
        ) as error:
            print(f"FAIL {phase}: {error}; later phases NOT RUN")
            return 1
    for name in completed:
        print("PASS " + name)
    print(
        "FORGEAI-ANALYST-DESIGN-EVAL-2 LOCAL VALIDATION PASSED â€” no live model; no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
