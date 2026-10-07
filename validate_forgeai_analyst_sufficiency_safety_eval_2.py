r"""Offline qualification: uv run python .alidate_forgeai_analyst_sufficiency_safety_eval_2.py.

FORGEAI-ANALYST-SUFFICIENCY-SAFETY-EVAL-2 (path-establishment correction).
No model, provider, Ollama or Docker. Revision 1 stays immutable and is
re-verified here. Scope is pinned before this slice.
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
BASE = "a90d176588aa30758cdda09f867ef8b1964a1376"  # revision 1 qualification recorded
SELF = "validate_forgeai_analyst_sufficiency_safety_eval_2.py"
PACKAGE = "evaluation/analyst_sufficiency_safety_eval2"
TEST = "evaluation/tests/test_analyst_sufficiency_safety_eval2.py"
TEST1 = "evaluation/tests/test_analyst_sufficiency_safety_eval1.py"
PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-EVAL-2.md"
PLAN1 = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-EVAL-1.md"
REV1 = "examples/forgeai/evaluation/analyst_sufficiency_safety_eval1"
DIAGNOSTIC = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-DIAGNOSTIC-1.md"
SMOKE3 = "examples/forgeai/live1-smoke-bf448d5a12b3"
SMOKE3_INVENTORY = "db18ea7f48168f90019a30f34ffadf78ab973a86fe329f9480d83acde8f1b14f"
ALLOWED = {
    SELF,
    "examples/forgeai/" + TEST,
    PLAN,
    REV1 + "/README.md",  # version-selection note only
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
} | {
    "examples/forgeai/" + PACKAGE + "/" + name
    for name in (
        "__init__.py",
        "README.md",
        "REVISION-DELTA.md",
        "CASES.md",
        "data.py",
        "scoring.py",
        "metrics.py",
        "runner.py",
        "report.py",
        "fixtures-s2.json",
        "inputs-s2.json",
        "oracle-s2.json",
        "gates-s2.json",
        "schema-s2.json",
        "freeze-s2.json",
    )
}
PROTECTED = (
    "src",
    "packages",
    "adrs",
    "examples/forgeai/src",
    "examples/forgeai/evaluation/analyst_design_eval1",
    "examples/forgeai/evaluation/analyst_design_eval2",
    "examples/forgeai/evaluation/analyst_evidence_loop",
    "examples/forgeai/evaluation/analyst_design_live1",
    "examples/forgeai/" + TEST1,
    "planning/FORGEAI-ANALYST-SUFFICIENCY-LIVE-PROFILE-1.md",
    "planning/FORGEAI-ANALYST-DESIGN-LIVE-1-DECISION.md",
    DIAGNOSTIC,
    PLAN1,
) + tuple(
    REV1 + "/" + name
    for name in (
        "__init__.py",
        "CASES.md",
        "data.py",
        "scoring.py",
        "metrics.py",
        "runner.py",
        "report.py",
        "fixtures-s1.json",
        "inputs-s1.json",
        "oracle-s1.json",
        "gates-s1.json",
        "schema-s1.json",
        "freeze-s1.json",
    )
)
COVERAGE = [
    ("revision-1 freeze intact", "revision1_freeze_and_record_intact"),
    ("revision-1 qualification record intact", "revision1_freeze_and_record_intact"),
    ("revision-1 never used live", "revision1_never_used_live"),
    ("revision-2 distinct identity", "distinct_revision2_identity_and_freeze"),
    ("same intended 22-case membership", "same_membership_content_and_inputs"),
    ("attack taxonomy preserved", "taxonomy_critical_set_pairs_and_gates_preserved"),
    ("benign controls preserved", "taxonomy_critical_set_pairs_and_gates_preserved"),
    ("critical set preserved", "taxonomy_critical_set_pairs_and_gates_preserved"),
    ("gates preserved", "taxonomy_critical_set_pairs_and_gates_preserved"),
    (
        "decision precedence preserved",
        "taxonomy_critical_set_pairs_and_gates_preserved",
    ),
    ("affected cases require source_role", "affected_cases_now_require_source_role"),
    ("import inference removed", "revision1_defect_mutation_is_caught"),
    (
        "required named paths model-visible",
        "every_required_named_path_is_model_visible",
    ),
    ("exact supplied path recognized", "a_supplied_exact_path_is_established"),
    ("explicit textual path recognized", "b_explicitly_written_path_is_established"),
    (
        "explicit declaration mapping recognized",
        "c_application_declaration_is_established",
    ),
    ("plain import not a path", "d_e_imports_do_not_establish_paths[foo/bar.py]"),
    ("from-import not a path", "d_e_imports_do_not_establish_paths[jobs/limits.py]"),
    (
        "package import not a path",
        "f_package_import_does_not_infer_init[pkg/__init__.py]",
    ),
    (
        "role-only dependency supports SOURCE_ROLE",
        "g_unresolved_import_supports_source_role",
    ),
    ("guessed .py path fabricated", "h_guessed_conventional_path_is_fabricated"),
    ("declaration-is-not-content", "i_declaration_establishes_location_not_content"),
    (
        "declared-but-unsupplied remains missing",
        "j_named_request_to_declared_file_remains_missing",
    ),
    ("d09-style invention still fails", "k_d09_style_invention_still_fails"),
    (
        "import-derived guesses counted fabricated",
        "l_import_derived_guesses_are_counted_as_fabricated",
    ),
    ("request recall preserved", "baseline_oracle_shaped_run_is_acceptable"),
    ("request precision preserved", "baseline_oracle_shaped_run_is_acceptable"),
    ("acceptable-set scoring preserved", "metrics_are_revision1_logic_rebound"),
    (
        "clarification intent mapping preserved",
        "flexible_role_and_intent_clarification_preserved",
    ),
    (
        "flexible SOURCE_ROLE handling preserved",
        "flexible_role_and_intent_clarification_preserved",
    ),
    (
        "critical false-sufficient gate unchanged",
        "safety_and_authority_gates_unchanged",
    ),
    ("authority gate unchanged", "safety_and_authority_gates_unchanged"),
    (
        "benign retention unchanged",
        "benign_retention_and_noncritical_reporting_unchanged",
    ),
    (
        "non-critical false-sufficient reported",
        "benign_retention_and_noncritical_reporting_unchanged",
    ),
    ("d21/d22 excluded", "d21_d22_excluded"),
    ("revision-1 defect mutation caught", "revision1_defect_mutation_is_caught"),
    ("payload leakage protections", "payload_leakage_protections"),
    ("freeze/digest protections", "tampered_revision2_artifact_refuses"),
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
    with tempfile.TemporaryDirectory(prefix="sufficiency-safety2-") as directory:
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
            phase("prerequisites (diagnostic, revision-1 record) and scope")
            text = (ROOT / DIAGNOSTIC).read_text(encoding="utf-8")
            if "Primary disposition: C" not in text or SMOKE3_INVENTORY not in text:
                raise ValueError("safety diagnostic 1 prerequisite missing")
            record = (ROOT / PLAN1).read_text(encoding="utf-8")
            if "LOCALLY QUALIFIED" not in record or "73/73" not in record:
                raise ValueError("revision-1 qualification record missing")
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
            report = temp / "safety.xml"
            tests(
                "offline revision-2 safety-condition qualification",
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
                "revision-1 safety evaluator regressions (immutable)",
                FORGE,
                TEST1,
            )
            tests(
                "design-eval revision-1 and revision-2 regressions",
                FORGE,
                "evaluation/tests/test_analyst_design_eval.py",
                "evaluation/tests/test_analyst_design_eval2.py",
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
                "LIVE-1 harness regressions",
                FORGE,
                "evaluation/tests/test_analyst_design_live1.py",
                "evaluation/tests/test_analyst_design_live1_fix.py",
                "evaluation/tests/test_analyst_design_live1_diag.py",
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
        "FORGEAI-ANALYST-SUFFICIENCY-SAFETY-EVAL-2 LOCAL VALIDATION PASSED"
        " — offline; no model; no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
