"""Offline operator qualification for ENG-ANALYST-SUFFICIENCY-AGENT-1."""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENG = ROOT / "packages/legoai-engineering"
FORGE = ROOT / "examples/forgeai"
BASE = "c2fdacce2f61611d19135bed24845b21453636ab"
SELF = "validate_engineering_analyst_sufficiency_agent_1.py"
AGENT = "src/legoai_engineering/analyst/sufficiency_agent.py"
DEFINITION = "src/legoai_engineering/analyst/sufficiency_definition.py"
TEST = "tests/test_sufficiency_agent.py"
INTEGRATION = "evaluation/tests/test_sufficiency_agent_integration.py"
ALLOWED = {
    "packages/legoai-engineering/" + x
    for x in (
        AGENT,
        DEFINITION,
        TEST,
        "tests/test_architecture.py",
        "tests/test_analyst_architecture.py",
        "docs/analyst-sufficiency-agent.md",
    )
} | {
    "examples/forgeai/" + INTEGRATION,
    SELF,
    "planning/FORGEAI-ANALYST-DESIGN-REASSESSMENT.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, encoding="utf-8"
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
        raise RuntimeError("unexpected changes: " + repr(sorted(changed - ALLOWED)))
    # Explicit immutable runtime/prompt/parser/fixture checks, even after a commit.
    for path in (
        "src",
        "adrs",
        "examples/forgeai/src",
        "examples/forgeai/evaluation/analyst_design_eval1",
        "examples/forgeai/evaluation/analyst_evidence_loop",
        "packages/legoai-engineering/src/legoai_engineering/analyst/api.py",
        "packages/legoai-engineering/src/legoai_engineering/analyst/values.py",
        "packages/legoai-engineering/src/legoai_engineering/analyst/sufficiency.py",
    ):
        if git("diff", "--name-only", BASE, "--", path):
            raise RuntimeError("protected artifact changed: " + path)
    decision = "planning/FORGEAI-ANALYST-DESIGN-REASSESSMENT.md"
    before = git("show", BASE + ":" + decision).replace("\r\n", "\n")
    if not (ROOT / decision).read_text(encoding="utf-8").startswith(before):
        raise RuntimeError("reassessment must be append-only")


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(UV_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    completed: list[str] = []
    phase = "initialization"
    with tempfile.TemporaryDirectory(prefix="sufficiency-agent-") as directory:
        temp = Path(directory)
        env["UV_CACHE_DIR"] = str(temp / "uv-cache")

        def start(name: str) -> None:
            nonlocal phase
            phase = name
            print("[PHASE] " + name, flush=True)

        def invoke(cwd: Path, *args: str) -> None:
            subprocess.run(
                ["uv", "run", "--locked", "--no-sync", "python", "-B", "-m", *args],
                cwd=cwd,
                env=env,
                check=True,
            )

        def tests(name: str, cwd: Path, *targets: str) -> None:
            start(name)
            xml = temp / (name.split()[0] + ".xml")
            invoke(
                cwd,
                "pytest",
                "-q",
                "-rs",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(temp / name.split()[0]),
                f"--junitxml={xml}",
                *targets,
            )
            cases = list(ET.parse(xml).getroot().iter("testcase"))
            if not cases or any(list(c) for c in cases):
                raise RuntimeError("tests must pass without skips or failures")
            completed.append(name)

        try:
            for name, path, marker in (
                (
                    "1 sufficiency-contract prerequisite",
                    ENG / "docs/analyst-sufficiency.md",
                    "37/37",
                ),
                (
                    "2 evidence-loop prerequisite",
                    FORGE / "evaluation/analyst_evidence_loop/README.md",
                    "42/42",
                ),
                (
                    "3 design-eval prerequisite",
                    FORGE / "evaluation/analyst_design_eval1/README.md",
                    "55/55",
                ),
            ):
                start(name)
                text = path.read_text(encoding="utf-8")
                if "LOCALLY QUALIFIED" not in text or marker not in text:
                    raise RuntimeError("prerequisite not qualified")
                completed.append(name)
            start("4 scope guard")
            scope()
            completed.append(phase)
            tests("5 new Agent public API and full contract suite", ENG, TEST)
            names = {
                c.attrib["name"].split("[")[0]
                for c in ET.parse(temp / "5.xml").getroot().iter("testcase")
            }
            coverage = [
                (
                    "6 distinct Agent definition/version",
                    "test_definition_and_governed_request",
                ),
                (
                    "7 RepositoryAnalyst 1.0.3 unchanged",
                    "test_definition_and_governed_request",
                ),
                (
                    "8 RepositoryAnalyst prompt unchanged",
                    "test_definition_and_governed_request",
                ),
                (
                    "9 RepositoryAnalyst parser unchanged",
                    "test_definition_and_governed_request",
                ),
                (
                    "10 provider-neutral ModelRequirement",
                    "test_definition_and_governed_request",
                ),
                (
                    "11 manifest serialization",
                    "test_complete_deterministic_input_and_no_hidden_metadata",
                ),
                (
                    "12 question serialization",
                    "test_complete_deterministic_input_and_no_hidden_metadata",
                ),
                (
                    "13 evidence serialization",
                    "test_complete_deterministic_input_and_no_hidden_metadata",
                ),
                (
                    "14 declared expectations serialization",
                    "test_complete_deterministic_input_and_no_hidden_metadata",
                ),
                (
                    "15 clarifications serialization",
                    "test_complete_deterministic_input_and_no_hidden_metadata",
                ),
                (
                    "16 explicit unknowns serialization",
                    "test_complete_deterministic_input_and_no_hidden_metadata",
                ),
                (
                    "17 no hidden oracle labels in input",
                    "test_complete_deterministic_input_and_no_hidden_metadata",
                ),
                (
                    "18 no hidden path leakage",
                    "test_complete_deterministic_input_and_no_hidden_metadata",
                ),
                (
                    "19 strict raw JSON acceptance",
                    "test_raw_fenced_dispositions_and_request_combinations",
                ),
                (
                    "20 strict fenced JSON acceptance",
                    "test_raw_fenced_dispositions_and_request_combinations",
                ),
                ("21 prose-around-JSON rejection", "test_invalid_output_no_retry"),
                ("22 unknown-field rejection", "test_invalid_output_no_retry"),
                ("23 missing-field rejection", "test_invalid_output_no_retry"),
                (
                    "24 disposition parsing",
                    "test_raw_fenced_dispositions_and_request_combinations",
                ),
                (
                    "25 named-evidence request parsing",
                    "test_raw_fenced_dispositions_and_request_combinations",
                ),
                (
                    "26 source-role request parsing",
                    "test_raw_fenced_dispositions_and_request_combinations",
                ),
                (
                    "27 operator-clarification parsing",
                    "test_raw_fenced_dispositions_and_request_combinations",
                ),
                (
                    "28 invented source-role path rejection",
                    "test_invalid_output_no_retry",
                ),
                ("29 request bounds", "test_invalid_output_no_retry"),
                ("30 explanation bounds", "test_invalid_output_no_retry"),
                (
                    "31 trusted manifest attribution",
                    "test_definition_and_governed_request",
                ),
                ("32 stale question rejection", "test_stale_input_never_rebound"),
                ("33 stale evidence rejection", "test_stale_input_never_rebound"),
                (
                    "34 prerequisites-unmet handling",
                    "test_prerequisites_unmet_not_semantic",
                ),
                ("35 invalid-output failure", "test_invalid_output_no_retry"),
                ("36 model-failure mapping", "test_model_failures"),
                ("37 no retry or repair", "test_invalid_output_no_retry"),
                (
                    "38 direct-sufficient scripted case",
                    "test_semantic_controls_are_scripted_contracts",
                ),
                (
                    "39 named-missing scripted case",
                    "test_semantic_controls_are_scripted_contracts",
                ),
                (
                    "40 source-role-missing scripted case",
                    "test_semantic_controls_are_scripted_contracts",
                ),
                (
                    "41 ambiguity scripted case",
                    "test_semantic_controls_are_scripted_contracts",
                ),
                (
                    "42 clarified ambiguity case",
                    "test_semantic_controls_are_scripted_contracts",
                ),
                (
                    "43 future-behavior control",
                    "test_semantic_controls_are_scripted_contracts",
                ),
                (
                    "44 unrelated-evidence control",
                    "test_semantic_controls_are_scripted_contracts",
                ),
                (
                    "45 malicious-content control",
                    "test_semantic_controls_are_scripted_contracts",
                ),
                (
                    "46 EvidenceRequest grants no authority",
                    "test_architecture_closed_imports_and_no_effect_surfaces",
                ),
                (
                    "47 SUFFICIENT grants no authority",
                    "test_architecture_closed_imports_and_no_effect_surfaces",
                ),
                (
                    "48 no filesystem/discovery imports",
                    "test_architecture_closed_imports_and_no_effect_surfaces",
                ),
                (
                    "49 no mutation imports",
                    "test_architecture_closed_imports_and_no_effect_surfaces",
                ),
                (
                    "50 no Workflow/Team/Planner",
                    "test_architecture_closed_imports_and_no_effect_surfaces",
                ),
                (
                    "51 frozen evaluator not imported",
                    "test_architecture_closed_imports_and_no_effect_surfaces",
                ),
            ]
            for name, test in coverage:
                start(name)
                if test not in names:
                    raise RuntimeError("missing passing coverage: " + test)
                print("  verified in phase 5: " + test)
                completed.append(name)
            tests(
                "52 evidence-loop integration and frozen vocabulary compatibility",
                FORGE,
                INTEGRATION,
            )
            tests(
                "53 sufficiency-contract regressions",
                ENG,
                "tests/test_analyst_sufficiency_contract.py",
            )
            tests(
                "54 evidence-loop regressions",
                FORGE,
                "evaluation/tests/test_analyst_evidence_loop.py",
            )
            tests(
                "55 design-eval regressions",
                FORGE,
                "evaluation/tests/test_analyst_design_eval.py",
            )
            tests(
                "56 RepositoryAnalyst regressions",
                ENG,
                "tests/test_analyst.py",
                "tests/test_json_document.py",
                "tests/test_analyst_prompt.py",
                "tests/test_analyst_sufficiency_prompt.py",
                "tests/test_analyst_sufficiency_semantics.py",
            )
            tests(
                "57 M7 Agent regressions",
                ROOT,
                "tests/unit/execution/test_agent.py",
                "tests/integration/composition/test_agent.py",
                "tests/architecture/test_agent.py",
            )
            tests(
                "58 ForgeAI worker regressions",
                FORGE,
                "tests/test_worker.py",
                "tests/test_architecture.py",
            )
            tests(
                "59 architecture and import guards",
                ENG,
                "tests/test_architecture.py",
                "tests/test_analyst_architecture.py",
            )
            start("60 no live/provider calls")
            if "test_architecture_closed_imports_and_no_effect_surfaces" not in names:
                raise RuntimeError("missing boundary guard")
            completed.append(phase)
            checked = [
                AGENT,
                DEFINITION,
                TEST,
                "tests/test_architecture.py",
                "tests/test_analyst_architecture.py",
                str(ROOT / SELF),
            ]
            start("61 mypy")
            invoke(ENG, "mypy", "--cache-dir", str(temp / "mypy-eng"), *checked)
            invoke(FORGE, "mypy", "--cache-dir", str(temp / "mypy-forge"), INTEGRATION)
            completed.append(phase)
            start("62 Ruff lint")
            invoke(ENG, "ruff", "check", "--no-cache", *checked)
            invoke(FORGE, "ruff", "check", "--no-cache", INTEGRATION)
            completed.append(phase)
            start("63 Ruff format")
            invoke(ENG, "ruff", "format", "--check", "--no-cache", *checked)
            invoke(FORGE, "ruff", "format", "--check", "--no-cache", INTEGRATION)
            completed.append(phase)
            start("64 git diff check")
            subprocess.run(["git", "diff", "--check", BASE], cwd=ROOT, check=True)
            # New unstaged/untracked files are also checked; git diff alone misses them.
            for name in ALLOWED:
                content = (ROOT / name).read_text(encoding="utf-8")
                if content.endswith("\n\n") or any(
                    line.rstrip() != line for line in content.splitlines()
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
        "ENG-ANALYST-SUFFICIENCY-AGENT-1 LOCAL VALIDATION PASSED — no live model; no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
