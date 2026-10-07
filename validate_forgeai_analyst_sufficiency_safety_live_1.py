r"""Offline qualification: uv run python .\validate_forgeai_analyst_sufficiency_safety_live_1.py.

FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-1 harness (forgeai-analyst-sufficiency-
safety-live/1). No model, provider, Ollama or Docker: every call is a scripted
Replay behind FORGEAI_LIVE1_OFFLINE=1. Passing does not authorize the baseline.
"""

import hashlib
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENG = ROOT / "packages/legoai-engineering"
BASE = "eb672778f4c4268f030efbcc093fad78d2732c2f"  # SAFETY-EVAL-2 qualification
SELF = "validate_forgeai_analyst_sufficiency_safety_live_1.py"
PACKAGE = "evaluation/analyst_sufficiency_safety_live1"
TEST = "evaluation/tests/test_analyst_sufficiency_safety_live1.py"
PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-1.md"
PLAN2 = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-EVAL-2.md"
PLAN1 = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-EVAL-1.md"
SMOKE3 = "examples/forgeai/live1-smoke-bf448d5a12b3"
SMOKE3_INVENTORY = "db18ea7f48168f90019a30f34ffadf78ab973a86fe329f9480d83acde8f1b14f"
ALLOWED = {
    SELF,
    "examples/forgeai/" + TEST,
    PLAN,
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
} | {
    "examples/forgeai/" + PACKAGE + "/" + name
    for name in (
        "__init__.py",
        "__main__.py",
        "README.md",
        "identity.py",
        "inputs.py",
        "harness.py",
        "storage.py",
        "report-schema.json",
    )
}
PROTECTED = (
    "src",
    "packages",
    "adrs",
    "examples/forgeai/src",
    "examples/forgeai/live1-smoke-d59e9c3f030b",
    "examples/forgeai/live1-smoke-227bdd3cec0b",
    SMOKE3,
    "examples/forgeai/evaluation/analyst_design_eval1",
    "examples/forgeai/evaluation/analyst_design_eval2",
    "examples/forgeai/evaluation/analyst_evidence_loop",
    "examples/forgeai/evaluation/analyst_design_live1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval2",
    "examples/forgeai/evaluation/tests/test_analyst_sufficiency_safety_eval1.py",
    "examples/forgeai/evaluation/tests/test_analyst_sufficiency_safety_eval2.py",
    "planning/FORGEAI-ANALYST-SUFFICIENCY-LIVE-PROFILE-1.md",
    "planning/FORGEAI-ANALYST-DESIGN-LIVE-1-DECISION.md",
    "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-DIAGNOSTIC-1.md",
    PLAN1,
    PLAN2,
)
COVERAGE = [
    ("revision-2-only admission", "revision2_only_admission"),
    ("revision-1 rejection", "revision1_rejection"),
    ("freeze digest verification", "freeze_digest_verification"),
    ("exact 22-case membership", "exact_22_case_membership"),
    ("fixed order", "fixed_order"),
    ("one-call-per-case ceiling", "one_call_per_case_ceiling"),
    ("no retry", "no_retry"),
    ("no reassessment", "no_reassessment"),
    ("no acquisition", "no_acquisition"),
    ("governed Agent path", "governed_agent_path"),
    ("payload leakage guard", "payload_leakage_guard"),
    ("complete request sets", "complete_request_sets"),
    ("path semantics revision 2", "path_semantics_revision2"),
    ("SOURCE_ROLE handling", "source_role_handling"),
    ("clarification handling", "clarification_handling"),
    ("critical false-sufficient counting", "critical_false_sufficient_counting"),
    (
        "non-critical false-sufficient reporting",
        "noncritical_false_sufficient_reporting",
    ),
    ("progression observation", "progression_observation"),
    ("authority counting", "authority_counting"),
    ("secret-path request", "secret_path_request"),
    ("edit-target request", "edit_target_request"),
    ("fabricated-path counting", "fabricated_path_counting"),
    ("forbidden-request counting", "forbidden_request_counting"),
    (
        "invalid output denominator retention",
        "invalid_output_denominator_retention",
    ),
    ("parser diagnostics", "parser_diagnostics"),
    ("lifecycle partition", "lifecycle_partition"),
    ("attempted invariant", "attempted_invariant"),
    ("planned invariant", "planned_invariant"),
    ("timeout behavior", "timeout_behavior"),
    ("runtime failure custody", "runtime_failure_custody"),
    ("no automatic replay", "no_automatic_replay"),
    ("effect UNKNOWN preservation", "effect_unknown_preservation"),
    ("total-call ceiling", "total_call_ceiling"),
    ("per-call timeout", "per_call_timeout"),
    ("total timeout", "total_timeout"),
    ("immutable run directory", "immutable_run_directory"),
    ("report schema", "report_schema"),
    ("A-G decision precedence (G)", "decision_precedence[faults0-G]"),
    ("A-G decision precedence (C)", "decision_precedence[faults1-C]"),
    ("A-G decision precedence (B)", "decision_precedence[faults2-B]"),
    ("A-G decision precedence (D)", "decision_precedence[faults3-D]"),
    ("A-G decision precedence (E)", "decision_precedence[faults4-E]"),
    ("A-G decision precedence (A)", "payload_leakage_guard"),
    ("F success condition", "f_success_condition"),
    ("no blended score", "no_blended_score"),
    ("historical artifacts unchanged", "historical_artifacts_unchanged"),
    ("no Agent/prompt/parser changes", "no_agent_prompt_parser_changes"),
    ("no evaluator changes", "no_evaluator_changes"),
    ("no hardening", "no_hardening"),
    ("zero model calls (offline fence)", "harness_is_offline_and_public"),
    ("preflight zero semantic calls", "preflight_zero_semantic_calls"),
    ("preflight refusals", "preflight_refusals"),
    ("preflight refusal custody", "preflight_refusal_is_recorded_without_calls"),
]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(
        UV_OFFLINE="1",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONUTF8="1",
        FORGEAI_LIVE1_OFFLINE="1",
    )
    done: list[str] = []
    current = "initialization"
    with tempfile.TemporaryDirectory(prefix="sufficiency-safety-live1-") as directory:
        temp = Path(directory)
        env["UV_CACHE_DIR"] = str(temp / "uv-cache")
        number = 0

        def phase(label: str) -> None:
            nonlocal current, number
            number += 1
            current = f"{number} {label}"
            print("[PHASE] " + current, flush=True)

        def run(cwd: Path, *args: str) -> None:
            subprocess.run(
                ["uv", "run", "--locked", "--no-sync", "python", "-B", "-m", *args],
                cwd=cwd,
                env=env,
                check=True,
            )

        def tests(label: str, cwd: Path, *targets: str) -> None:
            phase(label)
            run(
                cwd,
                "pytest",
                "-q",
                "-rs",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(temp / str(number)),
                *targets,
            )
            done.append(current)

        try:
            phase("SAFETY-EVAL-2 qualification prerequisite and scope")
            record = (ROOT / PLAN2).read_text(encoding="utf-8")
            if "LOCALLY QUALIFIED" not in record or "54/54" not in record:
                raise ValueError("SAFETY-EVAL-2 qualification record missing")
            changed = set(git("diff", "--name-only", BASE).splitlines())
            changed.update(
                git(
                    "ls-files",
                    "--others",
                    "--exclude-standard",
                    "--",
                    "src",
                    "packages",
                    "examples",
                    "planning",
                    SELF,
                ).splitlines()
            )
            if changed - ALLOWED:
                raise ValueError("unexpected files: " + repr(sorted(changed - ALLOWED)))
            for path in PROTECTED:
                if git("diff", "--name-only", BASE, "--", path):
                    raise ValueError("protected input changed: " + path)
            done.append(current)
            phase("Smoke 3 historical artifacts unchanged")
            smoke = sorted((ROOT / SMOKE3).iterdir(), key=lambda p: p.name)
            listing = "".join(
                f"{hashlib.sha256(p.read_bytes()).hexdigest()} *{p.name}\n"
                for p in smoke
            )
            if (
                len(smoke) != 81
                or hashlib.sha256(listing.encode()).hexdigest() != SMOKE3_INVENTORY
            ):
                raise ValueError("smoke 3 artifacts differ from the recorded inventory")
            done.append(current)
            phase("frozen identities, revision-1 rejection, no live run directory")
            subprocess.run(
                [
                    "uv",
                    "run",
                    "--locked",
                    "--no-sync",
                    "python",
                    "-B",
                    "-c",
                    "from analyst_sufficiency_safety_live1 import identity as i\n"
                    "b = i.binding()\n"
                    "assert b['evaluation'] == "
                    "'forgeai-analyst-sufficiency-safety-eval/2'\n"
                    "assert b['membership'] == [f's{n:02}' for n in range(1, 23)]\n"
                    "assert (b['call_ceiling'], b['call_seconds'], "
                    "b['total_seconds']) == (22, 600, 3600)\n"
                    "try:\n"
                    "    i.admit('forgeai-analyst-sufficiency-safety-eval/1')\n"
                    "except ValueError:\n"
                    "    pass\n"
                    "else:\n"
                    "    raise SystemExit('revision 1 admitted')\n",
                ],
                cwd=FORGE / "evaluation",
                env=env,
                check=True,
            )
            live = [
                p.name
                for p in (ROOT / "examples/forgeai").iterdir()
                if p.name.startswith(("safety-live", "sufficiency-safety-live"))
            ]
            if live:
                raise ValueError("live run directory present: " + repr(live))
            done.append(current)
            report = temp / "live.xml"
            tests(
                "offline safety live harness tests",
                FORGE,
                TEST,
                f"--junitxml={report}",
            )
            cases = list(ET.parse(report).getroot().iter("testcase"))
            if not cases or any(list(c) for c in cases):
                raise ValueError("no failed/skipped qualification cases allowed")
            names = {c.attrib["name"] for c in cases}
            names |= {n.split("[")[0] for n in names}
            for label, case in COVERAGE:
                phase(label)
                if "test_" + case not in names:
                    raise ValueError("passing evidence missing: " + case)
                print("  verified: " + case)
                done.append(current)
            tests(
                "SAFETY-EVAL-2 regressions",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_eval2.py",
            )
            tests(
                "SAFETY-EVAL-1 regressions (immutable)",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_eval1.py",
            )
            tests(
                "LIVE-1 harness regressions",
                FORGE,
                "evaluation/tests/test_analyst_design_live1.py",
                "evaluation/tests/test_analyst_design_live1_fix.py",
                "evaluation/tests/test_analyst_design_live1_diag.py",
            )
            tests(
                "sufficiency-Agent regressions", ENG, "tests/test_sufficiency_agent.py"
            )
            tests(
                "evidence-loop regressions",
                FORGE,
                "evaluation/tests/test_analyst_evidence_loop.py",
            )
            tests(
                "RepositoryAnalyst regressions",
                ENG,
                "tests/test_analyst.py",
                "tests/test_json_document.py",
                "tests/test_analyst_prompt.py",
                "tests/test_analyst_sufficiency_prompt.py",
                "tests/test_analyst_sufficiency_semantics.py",
            )
            tests(
                "ForgeAI worker regressions",
                FORGE,
                "tests/test_worker.py",
                "tests/test_architecture.py",
            )
            tests(
                "architecture/import guards",
                ROOT,
                "tests/unit/execution/test_agent.py",
                "tests/integration/composition/test_agent.py",
                "tests/architecture/test_agent.py",
            )
            phase("validator performs zero model/provider calls")
            if (
                env["FORGEAI_LIVE1_OFFLINE"] != "1"
                or "test_harness_is_offline_and_public" not in names
            ):
                raise ValueError("offline guard missing")
            done.append(current)
            checked = [PACKAGE, TEST, str(ROOT / SELF)]
            phase("mypy")
            run(FORGE, "mypy", "--cache-dir", str(temp / "mypy"), *checked)
            done.append(current)
            phase("Ruff lint")
            run(FORGE, "ruff", "check", "--no-cache", *checked)
            done.append(current)
            phase("Ruff format")
            run(FORGE, "ruff", "format", "--check", "--no-cache", *checked)
            done.append(current)
            phase("git diff --check")
            git("diff", "--check", BASE)
            for name in sorted(ALLOWED):
                value = (ROOT / name).read_text(encoding="utf-8")
                if (
                    not value.endswith("\n")
                    or value.endswith("\n\n")
                    or any(line != line.rstrip() for line in value.splitlines())
                ):
                    raise ValueError("whitespace: " + name)
            done.append(current)
        except (
            OSError,
            ValueError,
            RuntimeError,
            subprocess.CalledProcessError,
        ) as error:
            print(f"FAIL {current}: {error}; later phases NOT RUN")
            return 1
    for name in done:
        print("PASS " + name)
    print(
        "FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-1 HARNESS LOCAL VALIDATION PASSED"
        " — offline; no model; no Docker; baseline NOT authorized"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
