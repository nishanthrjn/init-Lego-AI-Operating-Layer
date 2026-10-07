r"""Offline qualification: uv run python .\validate_forgeai_analyst_sufficiency_safety_eval_1.py.

FORGEAI-ANALYST-SUFFICIENCY-SAFETY-EVAL-1. No model, provider, Ollama or Docker.
Scope is pinned before this slice, so it works before and after committing.
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
BASE = "89b1c642e69048b794925a85c36ab969ab6c9cab"  # safety diagnostic 1 recorded
SELF = "validate_forgeai_analyst_sufficiency_safety_eval_1.py"
PACKAGE = "evaluation/analyst_sufficiency_safety_eval1"
TEST = "evaluation/tests/test_analyst_sufficiency_safety_eval1.py"
PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-EVAL-1.md"
DIAGNOSTIC = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-DIAGNOSTIC-1.md"
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
        "README.md",
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
    "planning/FORGEAI-ANALYST-SUFFICIENCY-LIVE-PROFILE-1.md",
    "planning/FORGEAI-ANALYST-DESIGN-LIVE-1-DECISION.md",
    DIAGNOSTIC,
)
FAMILY = "attack_and_control_families"
COVERAGE = [
    (
        "d21/d22 excluded from gating denominator",
        "historical_cases_cannot_enter_denominator",
    ),
    ("distinct safety condition identity", "distinct_condition_identity_and_freeze"),
    ("distinct fixture identity", "distinct_condition_identity_and_freeze"),
    ("distinct oracle identity", "distinct_condition_identity_and_freeze"),
    ("distinct schema identity", "distinct_condition_identity_and_freeze"),
    ("distinct gate identity", "distinct_condition_identity_and_freeze"),
    ("frozen digests", "tampered_artifact_refuses"),
    ("independent case IDs", "independent_case_ids_and_membership"),
    ("independence from exposed d21/d22", "independence_from_exposed_cases"),
    ("self-authority attacks", FAMILY + "[self_asserted_authority]"),
    ("false-sufficiency attacks", FAMILY + "[false_sufficiency_claim]"),
    ("fake-system attacks", FAMILY + "[fake_role_delimiters]"),
    ("embedded-JSON attacks", FAMILY + "[embedded_output_json]"),
    ("secret-path attacks", FAMILY + "[secret_path_request]"),
    ("edit-authority attacks", FAMILY + "[edit_authority_expansion]"),
    ("false-governing-source attacks", FAMILY + "[false_governing_source]"),
    ("reference-is-not-content attacks", FAMILY + "[reference_as_content]"),
    ("source-role fabrication pressure", FAMILY + "[role_path_pressure]"),
    ("clarification hijack attacks", FAMILY + "[clarification_hijack]"),
    ("security-doc benign controls", FAMILY + "[control_security_documentation]"),
    ("quoted-attack benign controls", FAMILY + "[control_quoted_attack]"),
    ("ordinary-authoritative controls", FAMILY + "[control_authoritative_term]"),
    ("ordinary-ignore controls", FAMILY + "[control_ignore_term]"),
    ("sufficient benign cases", FAMILY + "[benign_sufficient]"),
    ("missing-evidence benign cases", FAMILY + "[benign_named_missing]"),
    ("attack/benign paired cases", "pairs"),
    ("critical-set definition", "critical_set_definition"),
    ("no lexical oracle", "no_lexical_oracle"),
    (
        "required paths established by evidence",
        "required_named_paths_are_established_by_supplied_evidence",
    ),
    ("zero false-sufficient gate", "malicious_sufficient_detected"),
    ("zero authority-violation gate", "authority_request_detected"),
    ("benign retention gate", "blanket_abstention_detected"),
    ("request recall", "baseline_oracle_shaped_run_is_acceptable"),
    ("request precision", "baseline_oracle_shaped_run_is_acceptable"),
    ("acceptable request-set scoring", "request_scoring_rules"),
    ("fabricated-path scoring", "fabricated_path_detected"),
    ("forbidden-request scoring", "authority_request_detected"),
    ("ambiguity accuracy", "ambiguity_hijack_detected"),
    ("reference-is-not-content accuracy", "ambiguity_and_reference_coverage"),
    ("benign false-positive measurement", "single_benign_abstention_is_reported"),
    ("structural validity", "invalid_output_stays_in_denominator"),
    ("operational failures", "invalid_output_stays_in_denominator"),
    ("all-attempt denominator", "invalid_output_stays_in_denominator"),
    ("no oracle label leakage", "no_oracle_category_or_hidden_path_leakage"),
    ("no category-label leakage", "no_oracle_category_or_hidden_path_leakage"),
    ("no hidden path leakage", "no_oracle_category_or_hidden_path_leakage"),
    ("malicious-sufficient mutation caught", "malicious_sufficient_detected"),
    ("dropped-critical-case mutation caught", "dropped_critical_case_detected"),
    ("keyword-filter mutation caught", "keyword_filter_detected"),
    ("benign-abstention mutation caught", "blanket_abstention_detected"),
    ("authority-ignore mutation caught", "authority_request_detected"),
    ("fabricated-path-ignore mutation caught", "fabricated_path_detected"),
    (
        "d21/d22 denominator mutation caught",
        "historical_cases_cannot_enter_denominator",
    ),
    ("payload-leak mutation caught", "payload_leak_mutation_detected"),
    (
        "non-critical false-sufficient reported",
        "noncritical_false_sufficient_reported_not_hidden",
    ),
    ("freeze/digest guard", "tampered_artifact_refuses"),
    (
        "report schema and no payload persistence",
        "report_schema_and_no_payload_persistence",
    ),
    (
        "Agent/prompt/parser/revision-2 pins unchanged",
        "agent_prompt_parser_and_eval2_unchanged",
    ),
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
    with tempfile.TemporaryDirectory(prefix="sufficiency-safety1-") as directory:
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
            phase("safety diagnostic prerequisite and scope")
            text = (ROOT / DIAGNOSTIC).read_text(encoding="utf-8")
            if "Primary disposition: C" not in text or SMOKE3_INVENTORY not in text:
                raise ValueError("safety diagnostic 1 prerequisite missing")
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
                "offline safety-condition qualification",
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
        "FORGEAI-ANALYST-SUFFICIENCY-SAFETY-EVAL-1 LOCAL VALIDATION PASSED"
        " — offline; no model; no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
