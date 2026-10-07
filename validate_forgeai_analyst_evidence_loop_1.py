r"""Offline operator qualification: uv run python .\validate_forgeai_analyst_evidence_loop_1.py."""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENG = ROOT / "packages/legoai-engineering"
BASE = "bb1465e940f362394b5dc9967652d2a960cb8538"
SELF = "validate_forgeai_analyst_evidence_loop_1.py"
TEST = "evaluation/tests/test_analyst_evidence_loop.py"
PACKAGE = "evaluation/analyst_evidence_loop"
DECISION = "planning/FORGEAI-ANALYST-DESIGN-REASSESSMENT.md"
ALLOWED = {
    SELF,
    DECISION,
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "examples/forgeai/" + TEST,
    *(
        "examples/forgeai/" + PACKAGE + "/" + name
        for name in ("__init__.py", "sequence.py", "README.md")
    ),
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
    with tempfile.TemporaryDirectory(prefix="analyst-loop-") as directory:
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
            start("1 sufficiency prerequisite locally qualified")
            guide = (ENG / "docs/analyst-sufficiency.md").read_text(encoding="utf-8")
            if (
                "**LOCALLY QUALIFIED**" not in guide
                or "37/37 phases passed" not in guide
            ):
                raise RuntimeError("operator-qualified prerequisite missing")
            completed.append(phase)
            start("2 scope guard")
            scope()
            completed.append(phase)
            report = temp / "flows.xml"
            tests(
                "3 evaluation-only placement and complete scripted suite",
                FORGE,
                TEST,
                f"--junitxml={report}",
            )
            cases = list(ET.parse(report).getroot().iter("testcase"))
            if not cases or any(list(c) for c in cases):
                raise RuntimeError("scripted suite must pass without skips/failures")
            names = {c.attrib["name"].split("[")[0] for c in cases}
            start("4 production worker and Agent runtime unchanged")
            if git(
                "diff",
                "--name-only",
                BASE,
                "--",
                "src",
                "packages",
                "examples/forgeai/src",
            ):
                raise RuntimeError("production sources or contracts changed")
            completed.append(phase)
            coverage = [
                ("5 directly sufficient", "directly_sufficient"),
                ("6 source-role acquisition", "source_role_acquisition"),
                ("7 operator clarification", "operator_clarification"),
                ("8 denied acquisition", "current_authority_each_read_and_release"),
                ("9 unavailable evidence", "acquisition_failures"),
                ("10 unresolved after one round", "still_insufficient_stops"),
                ("11 second round forbidden", "second_round_forbidden"),
                ("12 stale assessment", "stale_reassessment_and_review"),
                ("13 changed question stale", "stale_progression"),
                ("14 changed file content stale", "stale_progression"),
                ("15 source-role cannot self-resolve", "operator_selection_validation"),
                ("16 named request grants no authority", "named_request_no_authority"),
                ("17 clarification causes no read", "operator_clarification"),
                (
                    "18 unrelated evidence",
                    "unrelated_evidence_cannot_resolve_ambiguity",
                ),
                ("19 cumulative file count", "cumulative_file_limit"),
                ("20 cumulative byte limit", "cumulative_byte_limit"),
                ("21 question bound", "question_bound"),
                ("22 assessment call ceiling", "assessment_call_ceiling"),
                ("23 analysis call ceiling", "analysis_call_ceiling"),
                ("24 unique invocation identities", "duplicate_invocation_rejected"),
                (
                    "25 duplicate execution reuse forbidden",
                    "duplicate_invocation_rejected",
                ),
                ("26 no hidden retry", "operational_failure_no_retry"),
                (
                    "27 no edit-target promotion",
                    "no_target_promotion_and_safe_observation",
                ),
                ("28 no mutation authority", "architecture_guards"),
                (
                    "29 RepositoryEvidencePort authorized path",
                    "cannot_bypass_authorized_composition",
                ),
            ]
            for name, case in coverage:
                start(name)
                if "test_" + case not in names:
                    raise RuntimeError("missing passing case: " + case)
                print("  verified in phase 3: " + case)
                completed.append(name)
            tests(
                "30 AuthorizedRepositoryEvidence regressions",
                ENG,
                "tests/test_analyst.py",
            )
            tests(
                "31 sufficiency contract regressions",
                ENG,
                "tests/test_analyst_sufficiency_contract.py",
            )
            tests(
                "32 current RepositoryAnalyst regressions",
                ENG,
                "tests/test_json_document.py",
                "tests/test_analyst_prompt.py",
                "tests/test_analyst_sufficiency_prompt.py",
                "tests/test_analyst_sufficiency_semantics.py",
            )
            tests(
                "33 M7 Agent regressions",
                ROOT,
                "tests/unit/execution/test_agent.py",
                "tests/integration/composition/test_agent.py",
                "tests/architecture/test_agent.py",
            )
            tests(
                "34 ForgeAI worker regressions",
                FORGE,
                "tests/test_worker.py",
                "tests/test_architecture.py",
            )
            tests(
                "35 frozen R3/R4 regressions",
                FORGE,
                "evaluation/tests/test_analyst_quality_1q_r3.py",
                "evaluation/tests/test_analyst_quality_1q_r4.py",
            )
            tests(
                "36 architecture and import guards",
                ENG,
                "tests/test_architecture.py",
                "tests/test_analyst_architecture.py",
            )
            for name in (
                "37 no Workflow/Team/Planner",
                "38 no autonomous discovery or read bypass",
            ):
                start(name)
                if "test_architecture_guards" not in names:
                    raise RuntimeError("missing passing architecture guard")
                completed.append(name)
            checked = [PACKAGE, TEST, str(ROOT / SELF)]
            run("39 mypy", FORGE, "mypy", "--cache-dir", str(temp / "mypy"), *checked)
            run("40 Ruff lint", FORGE, "ruff", "check", "--no-cache", *checked)
            run(
                "41 Ruff format",
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *checked,
            )
            start("42 git diff check")
            subprocess.run(["git", "diff", "--check", BASE], cwd=ROOT, check=True)
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
        "FORGEAI-ANALYST-EVIDENCE-LOOP-1 LOCAL VALIDATION PASSED — no live model; no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
