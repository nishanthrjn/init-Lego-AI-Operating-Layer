r"""Offline operator qualification: uv run python .\validate_engineering_analyst_sufficiency_contract_1.py.

No live model, Docker, provider or acquisition orchestration. Phases 4-24
reference named passing cases from the single full contract suite in phase 3.
"""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENG = ROOT / "packages/legoai-engineering"
FORGE = ROOT / "examples/forgeai"
BASE = "594a0bceacaceee3864445a183f67a660e47fa5a"
SOURCE = "src/legoai_engineering/analyst/sufficiency.py"
TEST = "tests/test_analyst_sufficiency_contract.py"
SELF = "validate_engineering_analyst_sufficiency_contract_1.py"
DECISION = "planning/FORGEAI-ANALYST-DESIGN-REASSESSMENT.md"
ALLOWED = {
    "packages/legoai-engineering/" + p
    for p in (
        SOURCE,
        TEST,
        "tests/test_analyst_architecture.py",
        "tests/test_architecture.py",
        "docs/analyst-sufficiency.md",
    )
} | {SELF, DECISION, "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md"}


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
            # Historical generated pytest workspaces are not source changes.
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
        raise RuntimeError("unexpected scope: " + repr(sorted(changed - ALLOWED)))
    # The allowlist also pins all previous Analyst/Core/worker/history behavior.
    before = git("show", f"{BASE}:{DECISION}").replace("\r\n", "\n")
    if not (ROOT / DECISION).read_text(encoding="utf-8").startswith(before):
        raise RuntimeError("reassessment must be append-only")


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(UV_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    completed: list[str] = []
    phase = "initialization"
    with tempfile.TemporaryDirectory(prefix="analyst-contract-") as directory:
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
            start("1 reassessment decision present")
            if (
                "SEPARATE SUFFICIENCY + BOUNDED EVIDENCE ACQUISITION RECOMMENDED"
                not in (ROOT / DECISION).read_text(encoding="utf-8")
            ):
                raise RuntimeError("required design decision missing")
            completed.append(phase)
            start("2 scope and unchanged production/history guard")
            scope()
            completed.append(phase)
            report = temp / "contract.xml"
            tests(
                "3 public sufficiency values and complete contract suite",
                ENG,
                TEST,
                f"--junitxml={report}",
            )
            cases = list(ET.parse(report).getroot().iter("testcase"))
            if not cases or any(list(c) for c in cases):
                raise RuntimeError("contract suite must pass without skips/failures")
            names = {c.attrib["name"].split("[")[0] for c in cases}
            coverage = [
                ("4 dispositions", "public_values_and_dispositions"),
                ("5 evidence request kinds", "request_kinds_are_not_authority"),
                (
                    "6 manifest values",
                    "declared_role_binding_checks_membership_not_truth",
                ),
                ("7 question attribution", "exact_attribution_and_stale_rejection"),
                ("8 evidence attribution", "exact_attribution_and_stale_rejection"),
                ("9 stale rejection", "exact_attribution_and_stale_rejection"),
                ("10 changed question", "exact_attribution_and_stale_rejection"),
                (
                    "11 declared requirement presence",
                    "declared_role_binding_checks_membership_not_truth",
                ),
                ("12 missing requirement", "q21_missing_catalog_and_source_role"),
                (
                    "13 role request without invented path",
                    "request_kinds_are_not_authority",
                ),
                ("14 named request non-authority", "request_kinds_are_not_authority"),
                (
                    "15 clarification non-read authority",
                    "request_kinds_are_not_authority",
                ),
                ("16 q21", "q21_missing_catalog_and_source_role"),
                ("17 q22", "q22_clarification_and_unrelated_evidence"),
                ("18 q19", "q19_named_missing_implementation"),
                ("19 q11/q12", "future_behavior_controls"),
                ("20 c15", "future_behavior_controls"),
                ("21 unrelated evidence", "q22_clarification_and_unrelated_evidence"),
                ("22 duplicate expectations", "duplicate_expectations"),
                ("23 bounds", "bounds_and_invalid_values"),
                (
                    "24 safe repr and canonical identity serialization",
                    "identity_equality_hash_and_safe_repr",
                ),
            ]
            for name, case in coverage:
                start(name)
                if "test_" + case not in names:
                    raise RuntimeError("missing passing contract case: " + case)
                print("  verified in phase 3: " + case)
                completed.append(name)
            tests(
                "25 current parser regressions",
                ENG,
                "tests/test_json_document.py",
                "tests/test_analyst.py",
            )
            tests(
                "26 current Analyst tests",
                ENG,
                *[
                    str(p.relative_to(ENG))
                    for p in sorted((ENG / "tests").glob("test_analyst*.py"))
                    if p.name != Path(TEST).name
                ],
            )
            tests(
                "27 authorized evidence regressions",
                ENG,
                "tests/test_authorized_effects.py",
            )
            tests(
                "28 M7 Agent regressions",
                ROOT,
                "tests/unit/execution/test_agent.py",
                "tests/integration/composition/test_agent.py",
                "tests/architecture/test_agent.py",
            )
            tests(
                "29 ForgeAI worker regressions",
                FORGE,
                "tests/test_worker.py",
                "tests/test_architecture.py",
            )
            tests(
                "30 architecture and import boundaries",
                ROOT,
                "tests/architecture/test_import_boundaries.py",
            )
            tests(
                "31 no Workflow/Team or acquisition semantics",
                ENG,
                TEST + "::test_architecture_no_io_or_new_runtime",
                "tests/test_architecture.py",
            )
            tests(
                "32 inert imports no model/network effects",
                ENG,
                "tests/test_analyst_architecture.py",
            )
            checked = [
                SOURCE,
                TEST,
                "tests/test_analyst_architecture.py",
                str(ROOT / SELF),
                "tests/test_architecture.py",
            ]
            run("33 mypy", ENG, "mypy", "--cache-dir", str(temp / "mypy"), *checked)
            run("34 Ruff lint", ENG, "ruff", "check", "--no-cache", *checked)
            run(
                "35 Ruff format",
                ENG,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *checked,
            )
            start("36 git diff check")
            subprocess.run(["git", "diff", "--check", BASE], cwd=ROOT, check=True)
            completed.append(phase)
            tests(
                "37 frozen R3/R4 metrics and oracle regressions",
                FORGE,
                "evaluation/tests/test_analyst_quality_1q_r3.py",
                "evaluation/tests/test_analyst_quality_1q_r4.py",
            )
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
        "ENG-ANALYST-SUFFICIENCY-CONTRACT-1 LOCAL VALIDATION PASSED — no live model; no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
