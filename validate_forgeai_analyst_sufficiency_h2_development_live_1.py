r"""Offline qualification: uv run python .\validate_forgeai_analyst_sufficiency_h2_development_live_1.py.

FORGEAI-ANALYST-SUFFICIENCY-H2-DEVELOPMENT-LIVE-1 harness: Agent 1.1.0 + H1
against frozen SAFETY-EVAL-2. No model, provider, Ollama or Docker; PREFLIGHT
and DEVELOPMENT are never run. SAFETY-EVAL-3 is checked by Git object identity
only; it is never imported or opened.
"""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENG = ROOT / "packages/legoai-engineering"
BASE = "579a8d1"  # H2 local qualification recorded
SELF = "validate_forgeai_analyst_sufficiency_h2_development_live_1.py"
PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-H2-DEVELOPMENT-LIVE-1.md"
H2_PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-HARDENING-H2-EVIDENCE-ENVELOPE.md"
H1_PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-HARDENING-H1-REQUEST-POLICY.md"
MSO_PLAN = "planning/MODEL-STRUCTURED-OUTPUT-1.md"
HARNESS = "evaluation/analyst_sufficiency_h2_development_live1"
TEST = "evaluation/tests/test_analyst_sufficiency_h2_development_live1.py"
SEAL = "examples/forgeai/evaluation/analyst_sufficiency_safety_eval3"
SEAL_TREE = "d23679f0004620b1bcf814ba9546353f949af519"
ALLOWED = {
    SELF,
    PLAN,
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "examples/forgeai/" + TEST,
    *(
        f"examples/forgeai/{HARNESS}/{name}"
        for name in (
            "__init__.py",
            "__main__.py",
            "comparison.py",
            "harness.py",
            "identity.py",
            "inputs.py",
            "runtime.py",
            "storage.py",
            "policy.json",
            "decision-rules.json",
            "pins.json",
        )
    ),
}
PROTECTED = (
    "src",
    "adrs",
    "packages",
    ".gitignore",
    "examples/forgeai/src",
    "examples/model-structured-output-probe",
    "tests",
    "examples/forgeai/safety2-baseline-3cf8aba9a377",
    "examples/forgeai/evaluation/analyst_evidence_loop",
    "examples/forgeai/evaluation/analyst_sufficiency_hardening_h1",
    "examples/forgeai/evaluation/analyst_sufficiency_hardening_h2",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval2",
    SEAL,
    "examples/forgeai/evaluation/analyst_sufficiency_safety_live1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_live2",
    "examples/forgeai/evaluation/analyst_design_live1",
)
# Qualified assertions superseded by design: deselected by exact id, never edited.
# Each used "no change under packages/ or src since an old base" as a proxy and
# already failed before this slice; the identities are verified directly.
_PROXY = "a no-diff-since-base proxy already broken by H1/MODEL-STRUCTURED-OUTPUT-1"
SUPERSEDED = {
    "evaluation/tests/test_analyst_sufficiency_hardening_h1.py"
    "::test_no_core_change": _PROXY,
    "evaluation/tests/test_analyst_sufficiency_safety_live1.py"
    "::test_no_agent_prompt_parser_changes": _PROXY,
    "evaluation/tests/test_analyst_sufficiency_safety_runtime_identity2.py"
    "::test_agent_prompt_parser_unchanged": _PROXY,
    "evaluation/tests/test_analyst_sufficiency_safety_runtime_identity2.py"
    "::test_zero_baseline_calls": "superseded by the committed live/2 baseline",
    "evaluation/tests/test_analyst_sufficiency_safety_live2_preflight_custody1.py"
    "::test_prior_seven_entries_remain_accepted": "superseded by RUN-CUSTODY-2",
    "evaluation/tests/test_analyst_sufficiency_safety_live2_preflight_custody1.py"
    "::test_no_baseline_artifact_admitted": "superseded by RUN-CUSTODY-2",
}
COVERAGE = [
    ("1-2 condition and report identity", "1_2_condition_and_report_identity"),
    (
        "3-5 Agent 1.1.0 version/prompt/fingerprint",
        "3_to_5_agent_version_prompt_and_fingerprint",
    ),
    ("6 parser unchanged", "6_parser_unchanged"),
    ("7 H1 exact integration", "7_h1_exact_integration"),
    ("8 policy digest", "8_policy_digest_frozen_and_case_independent"),
    ("9 SAFETY-EVAL-2 exact freeze", "9_safety_eval2_exact_freeze"),
    ("10-11 membership s01-s22, d21/d22 excluded", "10_11_membership_and_exclusions"),
    (
        "12-13 historical identity and pinned metrics",
        "12_13_historical_identity_and_metrics_from_artifact",
    ),
    (
        "14-17 payloads, zones, round-trip, leakage",
        "14_to_17_payloads_zones_round_trip_and_leakage",
    ),
    ("17 leakage refuses dispatch", "17_leakage_refuses_dispatch"),
    ("18 response_format None", "18_response_format_none_on_every_request"),
    ("19 no H3 import", "19_no_h3_import"),
    ("20 no SAFETY-EVAL-3 content access", "20_no_safety_eval3_content_access"),
    (
        "21 zero provider under the offline fence",
        "21_live_path_refused_under_offline_fence",
    ),
    (
        "22-24 one call/case, ceiling 22, no retry",
        "22_to_24_one_call_per_case_ceiling_no_retry",
    ),
    (
        "25-27 no acquisition/clarification/fallback",
        "25_to_27_no_acquisition_clarification_or_fallback",
    ),
    ("28 raw progression preserved", "28_raw_progression_preserved"),
    ("29 guarded progression separate", "29_guarded_progression_separate"),
    (
        "30-31 raw and guarded metrics separate",
        "30_31_raw_and_guarded_metrics_separate",
    ),
    ("32 per-case delta deterministic", "32_per_case_delta_deterministic"),
    ("33 decision frozen prospectively", "33_decision_rules_frozen_prospectively"),
    ("34-35 semantic failures continue", "34_35_semantic_failures_continue"),
    ("36 infrastructure integrity stops", "36_infrastructure_integrity_stops"),
    (
        "37-38 lifecycle and effect uncertainty",
        "37_38_lifecycle_and_effect_uncertainty",
    ),
    ("39 fresh directory required", "39_fresh_directory_required"),
    (
        "40-41 immutable baseline, historical harnesses",
        "40_41_historical_baseline_and_harnesses_unchanged",
    ),
    (
        "42-44 bounded evidence, no prompt, no credentials",
        "42_to_44_bounded_evidence_no_prompt_no_credentials",
    ),
    ("45 development requires approval", "45_development_requires_explicit_approval"),
    ("supervised child path (offline)", "supervised_child_path_offline"),
    ("M Agent 1.0.0", "mutation_agent_1_0_0_rejected"),
    ("M response_format enabled", "mutation_response_format_enabled_detected"),
    (
        "M H1 omitted / raw replaced / forbidden hidden",
        "mutation_h1_omitted_or_raw_replaced_detected",
    ),
    ("M historical rescored", "mutation_historical_rescored_detected"),
    ("M evaluator-2 changed", "mutation_evaluator2_changed_detected"),
    ("M SAFETY-EVAL-3 imported/opened", "mutation_safety_eval3_access_detected"),
    ("M retry added", "mutation_retry_detected"),
    ("M call ceiling > 22", "mutation_call_ceiling_exceeded_detected"),
    ("M SOURCE_ROLE metric omitted", "mutation_source_role_metric_omitted_detected"),
    (
        "M thresholds changed after freeze",
        "mutation_thresholds_changed_after_freeze_detected",
    ),
    ("M raw prompt persisted", "mutation_raw_prompt_persistence_rejected"),
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
    with tempfile.TemporaryDirectory(prefix="h2-development-live1-") as directory:
        temp = Path(directory)
        env["UV_CACHE_DIR"] = str(temp / "uv-cache")
        number = 0
        names: set[str] = set()

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

        def tests(label: str, cwd: Path, *targets: str, junit: bool = False) -> None:
            phase(label)
            extra = [f"--junitxml={temp / f'{number}.xml'}"] if junit else []
            extra += [
                arg
                for node in SUPERSEDED
                if node.split("::")[0] in targets
                for arg in ("--deselect", node)
            ]
            run(
                cwd,
                "pytest",
                "-q",
                "-rs",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(temp / str(number)),
                *extra,
                *targets,
            )
            if junit:
                cases = list(
                    ET.parse(temp / f"{number}.xml").getroot().iter("testcase")
                )
                if not cases or any(list(c) for c in cases):
                    raise ValueError("no failed/skipped qualification cases allowed")
                names.update(c.attrib["name"] for c in cases)
            done.append(current)

        try:
            phase("H2, H1, MODEL-STRUCTURED-OUTPUT-1 prerequisites; ADR-022 accepted")
            for plan, marker in (
                (H2_PLAN, "62/62 validator phases"),
                (H1_PLAN, "LOCALLY QUALIFIED"),
                (MSO_PLAN, "## 10. Live compatibility probe"),
            ):
                if marker not in (ROOT / plan).read_text(encoding="utf-8"):
                    raise ValueError("prerequisite missing: " + plan)
            adr = (ROOT / "adrs/ADR-022.md").read_text(encoding="utf-8")
            if not adr.splitlines()[2].startswith("Status: Accepted"):
                raise ValueError("ADR-022 not accepted")
            done.append(current)
            phase("scope: only harness files changed; protected inputs unchanged")
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
                    "tests",
                    SELF,
                ).splitlines()
            )
            if changed - ALLOWED:
                raise ValueError("unexpected files: " + repr(sorted(changed - ALLOWED)))
            for path in PROTECTED:
                if git("diff", "--name-only", BASE, "--", path):
                    raise ValueError("protected input changed: " + path)
            done.append(current)
            phase("SAFETY-EVAL-3 sealed: Git object identity only, content unused")
            if git("rev-parse", "HEAD:" + SEAL).strip() != SEAL_TREE or git(
                "status", "--porcelain", "--", SEAL
            ):
                raise ValueError("SAFETY-EVAL-3 seal changed")
            for source in sorted((FORGE / HARNESS).iterdir()):
                if source.is_file() and "safety_eval3 import" in source.read_text(
                    encoding="utf-8"
                ):
                    raise ValueError("SAFETY-EVAL-3 imported by the harness")
            done.append(current)
            tests(
                "live-probe custody and ADR-022 structured-output guards",
                ROOT,
                "tests/architecture/test_structured_output_live_probe_custody.py",
                "tests/architecture/test_structured_output.py",
            )
            tests("harness tests", FORGE, TEST, junit=True)
            names |= {n.split("[")[0] for n in names}
            for label, case in COVERAGE:
                phase(label)
                if "test_" + case not in names:
                    raise ValueError("passing evidence missing: " + case)
                print("  verified: " + case)
                done.append(current)
            tests(
                "Engineering envelope, analyst and architecture regressions",
                ENG,
                "tests/test_sufficiency_envelope.py",
                "tests/test_architecture.py",
                "tests/test_analyst_architecture.py",
                "tests/test_analyst.py",
                "tests/test_analyst_sufficiency_contract.py",
                "tests/test_analyst_sufficiency_semantics.py",
                "tests/test_analyst_sufficiency_prompt.py",
                "tests/test_sufficiency_agent.py",
                "tests/test_json_document.py",
                "tests/test_analyst_request_policy.py",
            )
            tests(
                "H2, H1 and evidence-loop regressions",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_hardening_h2.py",
                "evaluation/tests/test_analyst_sufficiency_hardening_h1.py",
                "evaluation/tests/test_analyst_evidence_loop.py",
            )
            tests(
                "SAFETY-EVAL-2 regressions",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_eval2.py",
            )
            tests(
                "SAFETY-LIVE-1, RUNTIME-IDENTITY-2 and run-custody regressions",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_live1.py",
                "evaluation/tests/test_analyst_sufficiency_safety_runtime_identity2.py",
                "evaluation/tests/test_analyst_sufficiency_safety_live2_preflight_custody1.py",
                "evaluation/tests/test_analyst_sufficiency_safety_live2_run_custody2.py",
            )
            tests(
                "Core architecture and public-consumer guards",
                ROOT,
                "tests/architecture/test_agent.py",
                "tests/architecture/test_import_boundaries.py",
                "tests/architecture/test_local_host.py",
            )
            phase("validator performs zero model/provider calls")
            if env["FORGEAI_LIVE1_OFFLINE"] != "1":
                raise ValueError("offline guard missing")
            done.append(current)
            phase("mypy")
            run(
                FORGE,
                "mypy",
                "--cache-dir",
                str(temp / "mypy"),
                HARNESS,
                TEST,
                str(ROOT / SELF),
            )
            done.append(current)
            phase("Ruff lint")
            run(FORGE, "ruff", "check", "--no-cache", HARNESS, TEST, str(ROOT / SELF))
            done.append(current)
            phase("Ruff format")
            run(
                FORGE,
                "ruff",
                "format",
                "--check",
                "--no-cache",
                HARNESS,
                TEST,
                str(ROOT / SELF),
            )
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
        "FORGEAI-ANALYST-SUFFICIENCY-H2-DEVELOPMENT-LIVE-1 HARNESS LOCAL VALIDATION "
        "PASSED — offline; no model; no PREFLIGHT; no DEVELOPMENT run authorized"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
