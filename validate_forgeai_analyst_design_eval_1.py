r"""Offline operator qualification: uv run python .\validate_forgeai_analyst_design_eval_1.py."""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENG = ROOT / "packages/legoai-engineering"
BASE = "b31513a20afb8a502d6b8b074fee7845a50183fa"
SELF = "validate_forgeai_analyst_design_eval_1.py"
TEST = "evaluation/tests/test_analyst_design_eval.py"
PACKAGE = "evaluation/analyst_design_eval1"
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
        "runner.py",
        "metrics.py",
        "report.py",
        "README.md",
        "fixtures-v1.json",
        "oracle-v1.json",
        "gates-v1.json",
        "schema-v1.json",
        "freeze-v1.json",
        "CASES.md",
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
            for name, path, marker in (
                (
                    "1 sufficiency prerequisite",
                    ENG / "docs/analyst-sufficiency.md",
                    "37/37",
                ),
                (
                    "2 evidence-loop prerequisite",
                    FORGE / "evaluation/analyst_evidence_loop/README.md",
                    "42/42",
                ),
            ):
                start(name)
                text = path.read_text(encoding="utf-8")
                if "LOCALLY QUALIFIED" not in text or marker not in text:
                    raise RuntimeError("qualified prerequisite missing")
                completed.append(name)
            start("3 scope guard")
            scope()
            completed.append(phase)
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
                ("5 frozen fixture schema", "frozen_schema_identity_and_counts"),
                ("6 frozen oracle schema", "taxonomy_and_reviewable_oracles"),
                ("7 digest checks", "freeze_mutation_caught"),
                ("8 independent heldout cases", "frozen_schema_identity_and_counts"),
                ("9 directly sufficient", "taxonomy_and_reviewable_oracles"),
                ("10 named missing", "taxonomy_and_reviewable_oracles"),
                ("11 role missing", "taxonomy_and_reviewable_oracles"),
                ("12 ambiguity", "taxonomy_and_reviewable_oracles"),
                ("13 acquisition resolves", "resolving_and_unrelated_pairs"),
                ("14 clarification resolves", "resolving_and_unrelated_pairs"),
                ("15 unrelated negative pair", "resolving_and_unrelated_pairs"),
                ("16 future behavior", "taxonomy_and_reviewable_oracles"),
                ("17 multistep stop", "multistep_stops"),
                ("18 malicious content", "authority_is_measured_independently"),
                ("19 manifest error", "manifest_valid_is_not_truth"),
                ("20 operational failure", "operational_denominators"),
                ("21 q19-q22 nongating", "regressions_do_not_gate"),
                ("22 structural metric", "operational_denominators"),
                ("23 semantic metric", "reference_decision_and_all_denominators"),
                ("24 request metric", "operator_repair_never_rewrites_model_result"),
                ("25 false sufficient", "scripted_fault_detection"),
                ("26 false insufficient", "scripted_fault_detection"),
                ("27 transition metric", "resolving_and_unrelated_pairs"),
                ("28 authority metric", "authority_is_measured_independently"),
                (
                    "29 intervention accounting",
                    "operator_repair_never_rewrites_model_result",
                ),
                ("30 operational accounting", "operational_denominators"),
                ("31 grounding", "grounding_boundaries"),
                ("32 valid-only denominator", "operational_denominators"),
                ("33 all-attempt denominator", "operational_denominators"),
                ("34 blanket abstention fails", "scorer_mutation_tripwires"),
                (
                    "35 operator repair not model success",
                    "operator_repair_never_rewrites_model_result",
                ),
                ("36 oracle flip caught", "freeze_mutation_caught"),
                ("37 false-sufficient scorer mutation", "scorer_mutation_tripwires"),
                ("38 denominator mutation", "scorer_mutation_tripwires"),
                ("39 authority mutation", "scorer_mutation_tripwires"),
                ("40 stale mutation", "stale_manifest_controls"),
                ("41 unrelated mutation", "scorer_mutation_tripwires"),
                ("42 frozen artifact guard", "freeze_mutation_caught"),
            ]
            for name, case in coverage:
                start(name)
                if "test_" + case not in names:
                    raise RuntimeError("missing passing case: " + case)
                print("  verified in phase 4: " + case)
                completed.append(name)
            tests(
                "43 frozen R3/R4 regressions",
                FORGE,
                "evaluation/tests/test_analyst_quality_1q_r3.py",
                "evaluation/tests/test_analyst_quality_1q_r4.py",
            )
            tests(
                "44 evidence-loop regressions",
                FORGE,
                "evaluation/tests/test_analyst_evidence_loop.py",
            )
            tests(
                "45 sufficiency-contract regressions",
                ENG,
                "tests/test_analyst_sufficiency_contract.py",
            )
            tests(
                "46 current Analyst regressions",
                ENG,
                "tests/test_analyst.py",
                "tests/test_json_document.py",
                "tests/test_analyst_prompt.py",
                "tests/test_analyst_sufficiency_prompt.py",
                "tests/test_analyst_sufficiency_semantics.py",
            )
            tests(
                "47 M7 regressions",
                ROOT,
                "tests/unit/execution/test_agent.py",
                "tests/integration/composition/test_agent.py",
                "tests/architecture/test_agent.py",
            )
            tests(
                "48 worker regressions",
                FORGE,
                "tests/test_worker.py",
                "tests/test_architecture.py",
            )
            tests(
                "49 architecture and import guards",
                ENG,
                "tests/test_architecture.py",
                "tests/test_analyst_architecture.py",
            )
            start("50 no prompt/model/production changes")
            if git(
                "diff",
                "--name-only",
                BASE,
                "--",
                "src",
                "packages",
                "examples/forgeai/src",
            ):
                raise RuntimeError("production changed")
            completed.append(phase)
            start("51 no live/provider calls")
            if "test_architecture_no_prompt_or_live_path" not in names:
                raise RuntimeError("missing passing architecture guard")
            completed.append(phase)
            checked = [PACKAGE, TEST, str(ROOT / SELF)]
            run("52 mypy", FORGE, "mypy", "--cache-dir", str(temp / "mypy"), *checked)
            run("53 Ruff lint", FORGE, "ruff", "check", "--no-cache", *checked)
            run(
                "54 Ruff format",
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *checked,
            )
            start("55 git diff check")
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
        "FORGEAI-ANALYST-DESIGN-EVAL-1 LOCAL VALIDATION PASSED â€” no live model; no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
