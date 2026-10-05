r"""ENG-ANALYST-PROMPT-1 operator qualification. No live model, no Docker.

uv run python .\validate_engineering_analyst_prompt.py

Scope is pinned before this slice, so it works before and after committing.
Older validators' HEAD/base-relative scope guards reject this Analyst change;
they are not modified. Their regression suites run directly here.
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
BASE = "8d1ada3"  # ANALYST-CONTRACT-DIAG-1 live result recorded
API = "packages/legoai-engineering/src/legoai_engineering/analyst/api.py"
TEST = "tests/test_analyst_prompt.py"
EVALUATION = "examples/forgeai/evaluation/"
DIAG_DOC = "planning/FORGEAI-ANALYST-CONTRACT-DIAGNOSTIC.md"
PINNING = {
    EVALUATION + "content_discovery1/data.py",
    EVALUATION + "analyst_quality1q/data.py",
    EVALUATION + "analyst_quality1q/cli.py",
    EVALUATION + "analyst_contract_diag1/cli.py",
    EVALUATION + "tests/test_analyst_quality_1q.py",
    EVALUATION + "tests/test_analyst_contract_diag_1.py",
    EVALUATION + "tests/test_content_discovery_1.py",
}
ALLOWED = PINNING | {
    API,
    "packages/legoai-engineering/" + TEST,
    "packages/legoai-engineering/README.md",
    DIAG_DOC,
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "validate_engineering_analyst_prompt.py",
}
PRODUCTION = ("src/", "packages/legoai-engineering/src/", "examples/forgeai/src/")
DIAG_HISTORY = (
    EVALUATION + "analyst_contract_diag1/",
    EVALUATION + "run_analyst_contract_diag_1.py",
)
Q_HISTORY = (
    EVALUATION + "analyst_quality1q/",
    EVALUATION + "content_discovery1/",
    EVALUATION + "run_analyst_quality_1q.py",
    "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY.md",
    "planning/FORGEAI-CONTENT-DISCOVERY-EVALUATION.md",
)
ENGINEERING_CHECKED = ["src/legoai_engineering/analyst", TEST]
FORGE_CHECKED = [
    "evaluation/content_discovery1/data.py",
    "evaluation/analyst_quality1q",
    "evaluation/analyst_contract_diag1",
    "evaluation/tests/test_analyst_quality_1q.py",
    "evaluation/tests/test_analyst_contract_diag_1.py",
    "evaluation/tests/test_content_discovery_1.py",
    str(ROOT / "validate_engineering_analyst_prompt.py"),
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


def _normalized(text: str) -> str:
    return text.replace("\r\n", "\n")


def _untouched(prefixes: tuple[str, ...]) -> list[str]:
    return sorted(p for p in changed() - PINNING if p.startswith(prefixes))


def diag_history() -> None:
    touched = _untouched(DIAG_HISTORY)
    if touched:
        raise RuntimeError("DIAG-1 evidence changed: " + repr(touched))
    old = _normalized(git("show", f"{BASE}:{DIAG_DOC}"))
    new = _normalized((ROOT / DIAG_DOC).read_text(encoding="utf-8-sig"))
    if not new.startswith(old):
        raise RuntimeError("DIAG-1 results document is not append-only")


def q_history() -> None:
    touched = _untouched(Q_HISTORY)
    if touched:
        raise RuntimeError("1Q/CD-1 evidence changed: " + repr(touched))


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(PYTHONDONTWRITEBYTECODE="1", UV_OFFLINE="1")
    phase = "1 scope guard / production non-interference"
    completed: list[str] = []
    with tempfile.TemporaryDirectory(prefix="eng-analyst-prompt-1-") as temporary:
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

        def prompt(name: str, *selectors: str) -> None:
            pytest(name, ENGINEERING, *(f"{TEST}::{s}" for s in selectors))

        def rejected(name: str, *cases: str) -> None:
            prompt(
                name,
                *(
                    f"test_contract_violations_are_rejected_without_repair[{c}]"
                    for c in cases
                ),
            )

        def check(name: str, step: Callable[[], None]) -> None:
            nonlocal phase
            phase = name
            print("[PHASE] " + name, flush=True)
            step()
            completed.append(name)

        try:
            check(phase, scope)
            check("1b only Analyst version/instructions changed", definition_only)
            prompt("2 Analyst version 1.0.1", "test_definition_version_and_guidance")
            prompt(
                "3 exact six-field requirement in SYSTEM guidance",
                "test_definition_version_and_guidance",
                "test_governed_request_and_user_payload",
            )
            prompt(
                "4 risks independently specified",
                "test_risks_and_unknowns_are_each_their_own_required_field",
            )
            prompt(
                "5 unknowns independently specified",
                "test_risks_and_unknowns_are_each_their_own_required_field",
            )
            prompt(
                "6 compact six-field shape",
                "test_risks_and_unknowns_are_each_their_own_required_field",
                "test_governed_request_and_user_payload",
            )
            prompt("7 USER request unchanged", "test_governed_request_and_user_payload")
            prompt(
                "8 valid raw parsing unchanged",
                "test_valid_replies_are_accepted_unchanged[raw]",
                "test_valid_replies_are_accepted_unchanged[empty_narrative]",
            )
            prompt(
                "9 valid fenced parsing unchanged",
                "test_valid_replies_are_accepted_unchanged[fenced]",
            )
            rejected("10 missing risks rejected", "missing_risks")
            rejected("11 missing unknowns rejected", "missing_unknowns")
            rejected("12 missing both rejected", "missing_both")
            rejected("13 combined replacement field rejected", "combined_field")
            rejected("14 unexpected field rejected", "unexpected_field")
            rejected(
                "15 type/shape boundaries unchanged",
                "risks_type",
                "risks_null",
                "unknowns_type",
                "unknowns_blank",
                "risks_oversized",
                "unknowns_count",
                "findings_shape",
                "finding_entry",
                "relevant_files_shape",
                "relevant_files_duplicate",
            )
            prompt(
                "16 insufficient-evidence rule unchanged",
                "test_valid_replies_are_accepted_unchanged[insufficient]",
                "test_contract_violations_are_rejected_without_repair"
                "[insufficient_without_unknowns]",
                "test_contract_violations_are_rejected_without_repair"
                "[insufficient_with_findings]",
            )
            rejected(
                "17 membership rule unchanged",
                "membership_relevant",
                "membership_finding",
            )
            rejected("18 duplicate-key rejection unchanged", "duplicate_key")
            pytest(
                "19 Analyst regressions",
                ENGINEERING,
                TEST,
                "tests/test_analyst.py",
                "tests/test_analyst_architecture.py",
                "tests/test_json_document.py",
            )
            pytest(
                "20 AuthorizedRepositoryEvidence regressions",
                ENGINEERING,
                "tests/test_authorized_effects.py",
            )
            pytest(
                "21a DISCOVERY-1 regressions",
                ENGINEERING,
                "tests/test_structure.py",
                "tests/test_architecture.py",
            )
            pytest(
                "21b DISCOVERY-2A/2A.1 and CONTENT-DISCOVERY-1 regressions",
                FORGE,
                "evaluation/tests/test_discovery_2a.py",
                "evaluation/tests/test_discovery_2a1.py",
                "evaluation/tests/test_content_discovery_1.py",
            )
            pytest(
                "22 ForgeAI architecture regressions",
                FORGE,
                "tests/test_architecture.py",
                "evaluation/tests/test_lq1_architecture.py",
            )
            check("23a ANALYST-CONTRACT-DIAG-1 historical immutability", diag_history)
            pytest(
                "23b ANALYST-CONTRACT-DIAG-1 suite (pinned 1.0.0 identity)",
                FORGE,
                "evaluation/tests/test_analyst_contract_diag_1.py",
            )
            check("24a CONTENT-DISCOVERY-1Q historical immutability", q_history)
            pytest(
                "24b CONTENT-DISCOVERY-1Q suite (frozen inputs at foundation)",
                FORGE,
                "evaluation/tests/test_analyst_quality_1q.py",
            )
            run(
                "25a Engineering mypy",
                ENGINEERING,
                "mypy",
                "--cache-dir",
                str(temp / "mypy-engineering"),
                *ENGINEERING_CHECKED,
            )
            run(
                "25b ForgeAI evaluation and validator mypy",
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
                    f"26 {label} Ruff lint",
                    cwd,
                    "ruff",
                    "check",
                    "--no-cache",
                    *checked,
                )
                run(
                    f"27 {label} Ruff format",
                    cwd,
                    "ruff",
                    "format",
                    "--check",
                    "--no-cache",
                    *checked,
                )
            phase = "28 git diff --check"
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
        "ENG-ANALYST-PROMPT-1 LOCAL VALIDATION PASSED - Analyst 1.0.1 wording only; "
        "no live model, no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
