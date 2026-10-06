r"""ENG-ANALYST-SUFFICIENCY-SEMANTICS-1 operator qualification. No live model, no Docker.

uv run python .\validate_engineering_analyst_sufficiency_semantics.py

Scope is pinned before this slice, so it works before and after committing.
Older validators' scope guards reject this Analyst change; they are not
modified. Their regression suites run directly here.
"""

import ast
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENGINEERING = ROOT / "packages/legoai-engineering"
BASE = "cfeed1150fa4066b047b64cb308e85576c8bb3e0"  # SUFFICIENCY-SEMANTICS-DECISION
API = "packages/legoai-engineering/src/legoai_engineering/analyst/api.py"
TEST = "tests/test_analyst_sufficiency_semantics.py"
PROMPT_102 = "tests/test_analyst_sufficiency_prompt.py"
PROMPT_101 = "tests/test_analyst_prompt.py"
EVALUATION = "examples/forgeai/evaluation/"
DECISION = "planning/FORGEAI-ANALYST-SUFFICIENCY-SEMANTICS-DECISION.md"
PINNED_TESTS = {
    EVALUATION + "tests/test_analyst_quality_1q_r3.py",
    EVALUATION + "tests/test_analyst_model_compare_1.py",
    EVALUATION + "tests/test_content_discovery_1.py",
}
ALLOWED = PINNED_TESTS | {
    API,
    "packages/legoai-engineering/" + TEST,
    "packages/legoai-engineering/" + PROMPT_102,
    "packages/legoai-engineering/" + PROMPT_101,
    "packages/legoai-engineering/README.md",
    DECISION,
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "validate_engineering_analyst_sufficiency_semantics.py",
}
PRODUCTION = ("src/", "packages/legoai-engineering/src/", "examples/forgeai/src/")
R2_HISTORY = (
    EVALUATION + "analyst_quality1q_r2/",
    EVALUATION + "run_analyst_quality_1q_r2.py",
    EVALUATION + "tests/test_analyst_quality_1q_r2.py",
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R2.md",
)
DIAG_HISTORY = (
    EVALUATION + "analyst_insufficient_diag1/",
    EVALUATION + "run_analyst_insufficient_diag_1.py",
    EVALUATION + "tests/test_analyst_insufficient_diag_1.py",
    "planning/FORGEAI-ANALYST-INSUFFICIENT-DIAGNOSTIC.md",
    "planning/FORGEAI-ANALYST-ABSTENTION-DECISION.md",
)
R3_HISTORY = (
    EVALUATION + "analyst_quality1q_r3/",
    EVALUATION + "run_analyst_quality_1q_r3.py",
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R3.md",
)
COMPARE_HISTORY = (
    EVALUATION + "analyst_model_compare1/",
    EVALUATION + "run_analyst_model_compare_1.py",
    "planning/FORGEAI-ANALYST-MODEL-COMPARISON.md",
)
ORACLE_HISTORY = (
    EVALUATION + "analyst_quality1q/",
    EVALUATION + "content_discovery1/",
)
PARTITION = ROOT / EVALUATION / "analyst_quality1q/partition-v1.json"
ENGINEERING_CHECKED = [
    "src/legoai_engineering/analyst",
    TEST,
    PROMPT_102,
    PROMPT_101,
]
FORGE_CHECKED = [
    *(p.removeprefix("examples/forgeai/") for p in sorted(PINNED_TESTS)),
    str(ROOT / "validate_engineering_analyst_sufficiency_semantics.py"),
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
            ":(exclude)**/aq1q-r3-qwen2.5-coder-7b/**",
            ":(exclude)**/amc1-*/**",
        ).splitlines()
    )
    return paths


def scope() -> None:
    paths = changed()
    if paths - ALLOWED:
        raise RuntimeError("unexpected scope: " + repr(sorted(paths - ALLOWED)))
    production = sorted(p for p in paths if p.startswith(PRODUCTION) and p != API)
    if production:
        raise RuntimeError("production source changed: " + repr(production))


def append_only() -> None:
    old = git("show", f"{BASE}:{DECISION}").replace("\r\n", "\n")
    new = (ROOT / DECISION).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    if not new.startswith(old):
        raise RuntimeError("sufficiency semantics decision record is not append-only")


def _definition_call(tree: ast.AST) -> ast.Call:
    return next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == "AgentDefinition"
    )


def definition_only() -> None:
    """Only the version and instruction arguments of the Analyst differ."""
    before = ast.parse(git("show", f"{BASE}:{API}"))
    after = ast.parse((ROOT / API).read_text(encoding="utf-8"))
    old, new = _definition_call(before), _definition_call(after)
    if ast.dump(old.args[1]) == ast.dump(new.args[1]):
        raise RuntimeError("behavior version did not change")
    new.args[1:3] = old.args[1:3]
    if ast.dump(before) != ast.dump(after):
        raise RuntimeError("Analyst changed beyond version/instructions")


def untouched(prefixes: tuple[str, ...]) -> Callable[[], None]:
    def step() -> None:
        touched = sorted(p for p in changed() if p.startswith(prefixes))
        if touched:
            raise RuntimeError("historical evidence changed: " + repr(touched))

    return step


def c15_non_gating() -> None:
    """c15 stays a non-gating contract probe; the oracle inputs are unmodified."""
    untouched(ORACLE_HISTORY)()
    partition = json.loads(PARTITION.read_text(encoding="utf-8"))
    if "c15" not in partition["contract_probes"]:
        raise RuntimeError("c15 is no longer a contract probe")
    if "c15" in partition["supporting_quality"]:
        raise RuntimeError("c15 became a gating quality case")
    if partition["gating"] is not False:
        raise RuntimeError("contract-probe partition became gating")


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(PYTHONDONTWRITEBYTECODE="1", UV_OFFLINE="1")
    phase = "1a scope guard"
    completed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="eng-analyst-semantics-") as temporary:
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
            pytest(name, ENGINEERING, *(f"{TEST}::{s}" for s in selectors))

        def situation(name: str, case: str) -> None:
            tests(name, f"test_each_qualifying_situation[{case}]")

        def accepted(name: str, *cases: str) -> None:
            tests(name, *(f"test_accepted_replies[{c}]" for c in cases))

        def rejected(name: str, *cases: str) -> None:
            tests(name, *(f"test_rejected_replies_without_repair[{c}]" for c in cases))

        def check(name: str, step: Callable[[], None]) -> None:
            nonlocal phase
            phase = name
            print("[PHASE] " + name, flush=True)
            step()
            completed.append(name)

        try:
            check(phase, scope)
            check("1b decision record append-only", append_only)
            check(
                "2 production diff limited to Analyst version/instructions",
                definition_only,
            )
            tests("3a RepositoryAnalyst version 1.0.3", "test_version_and_budget")
            pytest(
                "3b version pinned by earlier prompt tests",
                ENGINEERING,
                f"{PROMPT_102}::test_version_and_identity",
                f"{PROMPT_101}::test_definition_version_and_guidance",
            )
            pytest(
                "4 six-field contract unchanged",
                ENGINEERING,
                f"{PROMPT_102}::test_six_field_contract_and_posture_are_preserved",
                f"{PROMPT_101}::test_risks_and_unknowns_are_each_their_own_required_field",
            )
            tests(
                "5 policy sentences exact and ordered",
                "test_policy_sentences_are_exact_and_ordered",
            )
            tests("6 governing evidence defined", "test_governing_evidence_is_defined")
            tests(
                "7 succeeded requires governing evidence",
                "test_succeeded_requires_governing_evidence_not_certainty",
            )
            tests(
                "8 succeeded means defensible, not certain",
                "test_succeeded_requires_governing_evidence_not_certainty",
            )
            tests(
                "9 insufficient lists exactly four situations",
                "test_insufficient_rule_lists_exactly_the_four_situations",
            )
            situation("10 implementation absent", "implementation")
            situation("11 authoritative data/config absent", "authoritative_source")
            situation("12a unresolved ambiguity among candidates", "ambiguity")
            tests("12b ambiguity rule", "test_ambiguity_rule")
            situation("13 relationship not establishable", "relationship")
            tests("14 reference is not content", "test_reference_is_not_content")
            tests(
                "15 unseen context vs missing governing evidence",
                "test_unseen_context_vs_missing_governing_evidence",
            )
            tests(
                "16 future behavior rule and its limit",
                "test_future_behavior_rule_and_its_limit",
            )
            tests(
                "17 relevance vs sufficiency, structural rule, generic wording",
                "test_relevance_and_structural_invariants",
                "test_policy_is_generic_and_grants_nothing",
            )
            tests(
                "18 SYSTEM request contains the policy",
                "test_governed_system_and_user_requests",
            )
            tests("19 USER request unchanged", "test_governed_system_and_user_requests")
            tests("20 prompt budget", "test_version_and_budget")
            accepted("21 valid raw parsing", "raw")
            accepted("22 valid fenced parsing", "fenced")
            accepted(
                "23 succeeded + risks/unknowns accepted", "succeeded_risks_unknowns"
            )
            accepted(
                "24 insufficient + relevant_files accepted",
                "insufficient_with_relevant_files",
                "insufficient_without_relevant_files",
            )
            rejected("25 insufficient + findings rejected", "insufficient_findings")
            rejected(
                "26 insufficient + empty unknowns rejected",
                "insufficient_empty_unknowns",
            )
            rejected(
                "27 field/type/bounds/membership regressions",
                "missing_field",
                "unexpected_field",
                "wrong_type",
                "bounds",
                "unknown_path",
            )
            rejected("28 duplicate-key regression", "duplicate_key")
            pytest(
                "29 Analyst regressions",
                ENGINEERING,
                TEST,
                PROMPT_102,
                PROMPT_101,
                "tests/test_analyst.py",
                "tests/test_analyst_architecture.py",
                "tests/test_json_document.py",
            )
            pytest(
                "30 AuthorizedRepositoryEvidence regressions",
                ENGINEERING,
                "tests/test_authorized_effects.py",
            )
            pytest(
                "31a DISCOVERY-1 regressions",
                ENGINEERING,
                "tests/test_structure.py",
                "tests/test_architecture.py",
            )
            pytest(
                "31b DISCOVERY-2A/2A.1, CONTENT-DISCOVERY-1, 1Q and DIAG-1 regressions",
                FORGE,
                "evaluation/tests/test_discovery_2a.py",
                "evaluation/tests/test_discovery_2a1.py",
                "evaluation/tests/test_content_discovery_1.py",
                "evaluation/tests/test_analyst_quality_1q.py",
                "evaluation/tests/test_analyst_contract_diag_1.py",
            )
            pytest(
                "32 ForgeAI architecture regressions",
                FORGE,
                "tests/test_architecture.py",
                "evaluation/tests/test_lq1_architecture.py",
            )
            check("33a CONTENT-DISCOVERY-1Q-R2 immutability", untouched(R2_HISTORY))
            pytest(
                "33b CONTENT-DISCOVERY-1Q-R2 pinned to 1.0.1",
                FORGE,
                "evaluation/tests/test_analyst_quality_1q_r2.py",
            )
            check(
                "34a ANALYST-INSUFFICIENT-DIAG-1 immutability", untouched(DIAG_HISTORY)
            )
            pytest(
                "34b ANALYST-INSUFFICIENT-DIAG-1 pinned to 1.0.1",
                FORGE,
                "evaluation/tests/test_analyst_insufficient_diag_1.py",
            )
            check("35a CONTENT-DISCOVERY-1Q-R3 immutability", untouched(R3_HISTORY))
            pytest(
                "35b CONTENT-DISCOVERY-1Q-R3 pinned to 1.0.2",
                FORGE,
                "evaluation/tests/test_analyst_quality_1q_r3.py",
            )
            check(
                "36a ANALYST-MODEL-COMPARE-1 immutability", untouched(COMPARE_HISTORY)
            )
            pytest(
                "36b ANALYST-MODEL-COMPARE-1 pinned to 1.0.2",
                FORGE,
                "evaluation/tests/test_analyst_model_compare_1.py",
            )
            check("37 c15 non-gating and unmodified", c15_non_gating)
            run(
                "38a Engineering mypy",
                ENGINEERING,
                "mypy",
                "--cache-dir",
                str(temp / "mypy-engineering"),
                *ENGINEERING_CHECKED,
            )
            run(
                "38b ForgeAI tests and validator mypy",
                FORGE,
                "mypy",
                "--cache-dir",
                str(temp / "mypy-forge"),
                *FORGE_CHECKED,
            )
            for label, cwd, checked in (
                ("Engineering", ENGINEERING, ENGINEERING_CHECKED),
                ("ForgeAI", FORGE, FORGE_CHECKED),
            ):
                run(
                    f"39 {label} Ruff lint",
                    cwd,
                    "ruff",
                    "check",
                    "--no-cache",
                    *checked,
                )
                run(
                    f"40 {label} Ruff format",
                    cwd,
                    "ruff",
                    "format",
                    "--check",
                    "--no-cache",
                    *checked,
                )
            phase = "41 git diff --check"
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
        "ENG-ANALYST-SUFFICIENCY-SEMANTICS-1 LOCAL VALIDATION PASSED - Analyst 1.0.3 "
        "guidance only; no live model, no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
