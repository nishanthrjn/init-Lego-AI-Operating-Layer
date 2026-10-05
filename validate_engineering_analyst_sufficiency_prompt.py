r"""ENG-ANALYST-SUFFICIENCY-PROMPT-1 operator qualification. No live model, no Docker.

uv run python .\validate_engineering_analyst_sufficiency_prompt.py

Scope is pinned before this slice, so it works before and after committing.
Older validators' scope guards reject this Analyst change; they are not
modified. Their regression suites run directly here.
"""

import ast
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENGINEERING = ROOT / "packages/legoai-engineering"
BASE = "dc8bacb916968267b1718c5c3480706add9e301f"  # ANALYST-ABSTENTION-DECISION-1
API = "packages/legoai-engineering/src/legoai_engineering/analyst/api.py"
TEST = "tests/test_analyst_sufficiency_prompt.py"
EVALUATION = "examples/forgeai/evaluation/"
DECISION = "planning/FORGEAI-ANALYST-ABSTENTION-DECISION.md"
PINNED_TESTS = {
    EVALUATION + "tests/test_analyst_quality_1q_r2.py",
    EVALUATION + "tests/test_analyst_insufficient_diag_1.py",
    EVALUATION + "tests/test_content_discovery_1.py",
}
ALLOWED = PINNED_TESTS | {
    API,
    "packages/legoai-engineering/" + TEST,
    "packages/legoai-engineering/tests/test_analyst_prompt.py",
    "packages/legoai-engineering/README.md",
    DECISION,
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "validate_engineering_analyst_sufficiency_prompt.py",
}
PRODUCTION = ("src/", "packages/legoai-engineering/src/", "examples/forgeai/src/")
R2_HISTORY = (
    EVALUATION + "analyst_quality1q_r2/",
    EVALUATION + "run_analyst_quality_1q_r2.py",
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY-R2.md",
)
DIAG_HISTORY = (
    EVALUATION + "analyst_insufficient_diag1/",
    EVALUATION + "run_analyst_insufficient_diag_1.py",
    "planning/FORGEAI-ANALYST-INSUFFICIENT-DIAGNOSTIC.md",
)
ENGINEERING_CHECKED = [
    "src/legoai_engineering/analyst",
    TEST,
    "tests/test_analyst_prompt.py",
]
FORGE_CHECKED = [
    *(p.removeprefix("examples/forgeai/") for p in sorted(PINNED_TESTS)),
    str(ROOT / "validate_engineering_analyst_sufficiency_prompt.py"),
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
    production = sorted(p for p in paths if p.startswith(PRODUCTION) and p != API)
    if production:
        raise RuntimeError("production source changed: " + repr(production))


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


def append_only() -> None:
    old = git("show", f"{BASE}:{DECISION}").replace("\r\n", "\n")
    new = (ROOT / DECISION).read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    if not new.startswith(old):
        raise RuntimeError("abstention decision record is not append-only")


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(PYTHONDONTWRITEBYTECODE="1", UV_OFFLINE="1")
    phase = "1 scope guard"
    completed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="eng-analyst-sufficiency-") as temporary:
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
            check(
                "2 production diff limited to Analyst version/instructions",
                definition_only,
            )
            tests("3 RepositoryAnalyst version 1.0.2", "test_version_and_identity")
            tests(
                "4 six-field contract unchanged",
                "test_six_field_contract_and_posture_are_preserved",
            )
            tests(
                "5 succeeded policy present",
                "test_status_policy_sentences_are_exact_and_ordered",
            )
            tests(
                "6 insufficient policy present",
                "test_status_policy_sentences_are_exact_and_ordered",
                "test_succeeded_is_defensible_not_certain",
            )
            tests(
                "7 residual uncertainty with succeeded allowed",
                "test_succeeded_is_defensible_not_certain",
            )
            tests(
                "8 risks/unknowns relationship to succeeded",
                "test_succeeded_is_defensible_not_certain",
                "test_structural_rule_is_explicit_and_unchanged",
            )
            tests(
                "9 requested-unimplemented behavior rule",
                "test_status_policy_sentences_are_exact_and_ordered",
                "test_policy_is_generic_and_grants_nothing",
            )
            tests(
                "10 insufficient findings=[] rule explicit",
                "test_structural_rule_is_explicit_and_unchanged",
            )
            tests(
                "11 insufficient unknowns non-empty rule explicit",
                "test_structural_rule_is_explicit_and_unchanged",
            )
            tests(
                "12 SYSTEM request contains the policy",
                "test_governed_system_and_user_requests",
            )
            tests("13 USER request unchanged", "test_governed_system_and_user_requests")
            tests("14 prompt budget", "test_version_and_identity")
            accepted("15 valid raw parsing", "raw")
            accepted("16 valid fenced parsing", "fenced")
            accepted(
                "17 succeeded + risks accepted",
                "succeeded_risks",
                "succeeded_findings",
                "succeeded_all",
            )
            accepted("18 succeeded + unknowns accepted", "succeeded_unknowns")
            rejected(
                "19 insufficient + findings rejected",
                "insufficient_findings",
                "insufficient_both",
            )
            rejected(
                "20 insufficient + empty unknowns rejected",
                "insufficient_empty_unknowns",
            )
            accepted("21 valid insufficient reply accepted", "insufficient_valid")
            rejected(
                "22 field/type/membership/bounds regressions",
                "missing_status",
                "missing_risks",
                "missing_unknowns",
                "unexpected_field",
                "status_value",
                "summary_type",
                "risks_type",
                "unknowns_type",
                "findings_type",
                "relevant_files_type",
                "unknown_relevant_path",
                "unknown_finding_path",
                "summary_bound",
                "risk_bound",
                "unknowns_count",
                "finding_text_bound",
            )
            rejected("23 duplicate-key regression", "duplicate_key")
            pytest(
                "24 Analyst regressions",
                ENGINEERING,
                TEST,
                "tests/test_analyst.py",
                "tests/test_analyst_architecture.py",
                "tests/test_json_document.py",
            )
            pytest(
                "25 AuthorizedRepositoryEvidence regressions",
                ENGINEERING,
                "tests/test_authorized_effects.py",
            )
            pytest(
                "26a DISCOVERY-1 regressions",
                ENGINEERING,
                "tests/test_structure.py",
                "tests/test_architecture.py",
            )
            pytest(
                "26b DISCOVERY-2A/2A.1, CONTENT-DISCOVERY-1, 1Q and DIAG-1 regressions",
                FORGE,
                "evaluation/tests/test_discovery_2a.py",
                "evaluation/tests/test_discovery_2a1.py",
                "evaluation/tests/test_content_discovery_1.py",
                "evaluation/tests/test_analyst_quality_1q.py",
                "evaluation/tests/test_analyst_contract_diag_1.py",
            )
            pytest(
                "27 ForgeAI architecture regressions",
                FORGE,
                "tests/test_architecture.py",
                "evaluation/tests/test_lq1_architecture.py",
            )
            pytest(
                "28 ENG-ANALYST-PROMPT-1 regressions",
                ENGINEERING,
                "tests/test_analyst_prompt.py",
            )
            check("29a CONTENT-DISCOVERY-1Q-R2 immutability", untouched(R2_HISTORY))
            pytest(
                "29b CONTENT-DISCOVERY-1Q-R2 pinned to 1.0.1",
                FORGE,
                "evaluation/tests/test_analyst_quality_1q_r2.py",
            )
            check(
                "30a ANALYST-INSUFFICIENT-DIAG-1 immutability", untouched(DIAG_HISTORY)
            )
            check("30b abstention decision record append-only", append_only)
            pytest(
                "30c ANALYST-INSUFFICIENT-DIAG-1 pinned to 1.0.1",
                FORGE,
                "evaluation/tests/test_analyst_insufficient_diag_1.py",
            )
            run(
                "31a Engineering mypy",
                ENGINEERING,
                "mypy",
                "--cache-dir",
                str(temp / "mypy-engineering"),
                *ENGINEERING_CHECKED,
            )
            run(
                "31b ForgeAI tests and validator mypy",
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
                    f"32 {label} Ruff lint",
                    cwd,
                    "ruff",
                    "check",
                    "--no-cache",
                    *checked,
                )
                run(
                    f"33 {label} Ruff format",
                    cwd,
                    "ruff",
                    "format",
                    "--check",
                    "--no-cache",
                    *checked,
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
        "ENG-ANALYST-SUFFICIENCY-PROMPT-1 LOCAL VALIDATION PASSED - Analyst 1.0.2 "
        "guidance only; no live model, no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
