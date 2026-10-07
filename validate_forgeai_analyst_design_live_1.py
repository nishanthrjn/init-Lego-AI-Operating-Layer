r"""Offline operator qualification: uv run python .\validate_forgeai_analyst_design_live_1.py."""

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
BASE = "3bfdd9235fb915b07d3a759f9b731dee5670e33f"
PACKAGE = "evaluation/analyst_design_live1"
TEST = "evaluation/tests/test_analyst_design_live1.py"
SELF = "validate_forgeai_analyst_design_live_1.py"
FIX_TEST = "evaluation/tests/test_analyst_design_live1_fix.py"
DIAG_TEST = "evaluation/tests/test_analyst_design_live1_diag.py"
DIAGNOSTIC_2 = "planning/FORGEAI-ANALYST-DESIGN-LIVE-1-SMOKE-FAILURE-DIAGNOSTIC-2.md"
ALLOWED = {
    SELF,
    "examples/forgeai/" + TEST,
    "examples/forgeai/" + FIX_TEST,
    "examples/forgeai/" + DIAG_TEST,
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "planning/FORGEAI-ANALYST-DESIGN-LIVE-1-CHILD-FAILURE-DIAGNOSTIC.md",
    DIAGNOSTIC_2,
} | {
    "examples/forgeai/" + PACKAGE + "/" + name
    for name in (
        "runtime.py",
        "diagnostics.py",
        "lifecycle.py",
        "storage.py",
        "harness.py",
        "README.md",
        "output_diagnostics.py",
    )
}
# Only these historical files may be untracked; phase 4 checks every byte
# against the inventory in the committed diagnostic. No directory-wide exemption.
HISTORY = {
    "examples/forgeai/live1-" + directory + "/" + name
    for directory, names in (
        ("preflight-411899d3f557", ("run.json", "report.json", "report.md")),
        (
            "smoke-d59e9c3f030b",
            (
                "run.json",
                "report.json",
                "report.md",
                "call-001-started.json",
                "call-001-finished.json",
            ),
        ),
    )
    for name in names
}
# Smoke 2 (cafee55d) and its preflight: byte-verified against DIAGNOSTIC_2.
SMOKE_2 = "examples/forgeai/live1-smoke-227bdd3cec0b"
PREFLIGHT_2 = "examples/forgeai/live1-preflight-9bdb9f5867b6"
SMOKE_2_INVENTORY = "68f4e1ae6a637010ab38ce361717a6d3a17c9f104d6e4b9f25ff9201539ecf6a"
PREFLIGHT_2_FILES = {
    "run.json": "14b5f3634903bbf99b1173ec91b7e41dec230c308bb27c4041d6631f0580f159",
    "report.json": "4cafdcf07b4b3dc215a7f650575a6897617c55837c85370315821113e99d8edb",
    "report.md": "4a02f2640ca563c70d1c031e09811fe0fcfcfc841c35192359b4420e68c1018d",
}


def smoke_2_history() -> set[str]:
    """Exactly the recorded smoke-2/preflight-2 files, every byte verified."""
    text = (ROOT / DIAGNOSTIC_2).read_text(encoding="utf-8")
    smoke = sorted((ROOT / SMOKE_2).iterdir(), key=lambda p: p.name)
    listing = "".join(
        f"{hashlib.sha256(p.read_bytes()).hexdigest()} *{p.name}\n" for p in smoke
    )
    if (
        SMOKE_2_INVENTORY not in text
        or len(smoke) != 55
        or hashlib.sha256(listing.encode()).hexdigest() != SMOKE_2_INVENTORY
    ):
        raise ValueError("smoke 2 artifacts differ from the recorded inventory")
    preflight = sorted(p.name for p in (ROOT / PREFLIGHT_2).iterdir())
    if preflight != sorted(PREFLIGHT_2_FILES) or any(
        value not in text
        or hashlib.sha256((ROOT / PREFLIGHT_2 / name).read_bytes()).hexdigest() != value
        for name, value in PREFLIGHT_2_FILES.items()
    ):
        raise ValueError("preflight 2 artifacts differ from the recorded hashes")
    return {f"{SMOKE_2}/{p.name}" for p in smoke} | {
        f"{PREFLIGHT_2}/{name}" for name in preflight
    }


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
    with tempfile.TemporaryDirectory(prefix="sufficiency-live1-") as directory:
        temp = Path(directory)
        env["UV_CACHE_DIR"] = str(temp / "uv-cache")

        def phase(number: int, label: str) -> None:
            nonlocal current
            current = f"{number} {label}"
            print("[PHASE] " + current, flush=True)

        def run(cwd: Path, *args: str) -> None:
            subprocess.run(
                ["uv", "run", "--locked", "--no-sync", "python", "-B", "-m", *args],
                cwd=cwd,
                env=env,
                check=True,
            )

        def tests(number: int, label: str, cwd: Path, *targets: str) -> None:
            phase(number, label)
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
            phase(1, "prerequisites and immutable scope")
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
            history_2 = smoke_2_history()
            if changed - ALLOWED - HISTORY - history_2:
                raise ValueError(
                    "unexpected files: "
                    + repr(sorted(changed - ALLOWED - HISTORY - history_2))
                )
            for name in (
                "ENG-ANALYST-SUFFICIENCY-CONTRACT-1",
                "FORGEAI-ANALYST-EVIDENCE-LOOP-1",
                "ENG-ANALYST-SUFFICIENCY-AGENT-1",
                "FORGEAI-ANALYST-DESIGN-EVAL-2",
            ):
                if name not in (
                    ROOT / "planning/FORGEAI-ANALYST-DESIGN-REASSESSMENT.md"
                ).read_text(encoding="utf-8"):
                    raise ValueError("qualification record missing: " + name)
            done.append(current)
            phase(2, "revision-2 and production unchanged")
            for path in (
                "src",
                "packages",
                "adrs",
                "examples/forgeai/src",
                "examples/forgeai/evaluation/analyst_design_eval1",
                "examples/forgeai/evaluation/analyst_design_eval2",
                "examples/forgeai/evaluation/analyst_evidence_loop",
            ):
                if git("diff", "--name-only", BASE, "--", path):
                    raise ValueError("protected input changed: " + path)
            done.append(current)
            phase(3, "profile and experiment decisions unchanged")
            for name in (
                "FORGEAI-ANALYST-SUFFICIENCY-LIVE-PROFILE-1.md",
                "FORGEAI-ANALYST-DESIGN-LIVE-1-DECISION.md",
            ):
                if git("diff", "--name-only", BASE, "--", "planning/" + name):
                    raise ValueError("decision changed")
            done.append(current)
            report = temp / "offline.xml"
            tests(
                4,
                "offline harness qualification",
                FORGE,
                TEST,
                FIX_TEST,
                DIAG_TEST,
                f"--junitxml={report}",
            )
            cases = list(ET.parse(report).getroot().iter("testcase"))
            if not cases or any(list(c) for c in cases):
                raise ValueError("no failed/skipped qualification cases allowed")
            names = {c.attrib["name"].split("[")[0] for c in cases}
            names |= {c.attrib["name"] for c in cases}  # parametrized evidence
            coverage = [
                ("live condition identity", "identity_preflight_zero_calls"),
                ("live report identity", "identity_preflight_zero_calls"),
                ("Agent 1.0.0 identity", "identity_preflight_zero_calls"),
                ("prompt digest binding", "identity_preflight_zero_calls"),
                ("parser identity binding", "identity_preflight_zero_calls"),
                ("14b pin", "identity_preflight_zero_calls"),
                ("expected model digest", "frozen_pin_mismatch"),
                ("local Ollama policy", "identity_preflight_zero_calls"),
                ("no credentials/remotes", "no_remote_or_credentials"),
                ("N=1", "identity_preflight_zero_calls"),
                ("smoke IDs/order", "identity_preflight_zero_calls"),
                ("smoke call ceiling", "smoke_order_no_followup_and_budget"),
                ("full call ceiling", "full_controller_68_calls_and_report"),
                ("timeout ceilings", "identity_preflight_zero_calls"),
                ("no final analysis", "architecture"),
                ("preflight zero calls", "identity_preflight_zero_calls"),
                ("clean tree guard", "dirty_and_uncommitted_refusal"),
                ("current commit capture", "identity_preflight_zero_calls"),
                ("output freshness", "storage_overwrite_and_identity"),
                ("run identity uniqueness", "storage_overwrite_and_identity"),
                ("leakage guard", "leakage_guard_before_model"),
                (
                    "actual governed Agent path",
                    "actual_governed_agent_complete_condition_parity",
                ),
                ("no copied prompt/ModelPort bypass", "architecture"),
                (
                    "EvidenceSequence reuse",
                    "actual_governed_agent_complete_condition_parity",
                ),
                ("complete request sets", "multi_and_mixed_no_repair"),
                ("mixed request behavior", "multi_and_mixed_no_repair"),
                ("no repair/retry/fallback", "interrupt_no_retry_and_custody"),
                (
                    "planned denominator preservation",
                    "conditional_stop_keeps_planned_denominator",
                ),
                (
                    "d27/d28 non-model controls",
                    "actual_governed_agent_complete_condition_parity",
                ),
                ("q19-q22 nongating", "regressions_nongating"),
                (
                    "profile metric parity",
                    "actual_governed_agent_complete_condition_parity",
                ),
                ("grounding NOT_MEASURED", "report_boundary_rejects_false_claims"),
                ("aggregate NOT_APPLICABLE", "report_boundary_rejects_false_claims"),
                ("outcome vocabulary", "outcomes"),
                ("outcome precedence", "precedence_and_incomplete_denominators"),
                ("unsafe precedence", "precedence_and_incomplete_denominators"),
                (
                    "supported gate mapping",
                    "actual_governed_agent_complete_condition_parity",
                ),
                ("blanket abstention failure", "outcomes"),
                (
                    "operational controls",
                    "actual_governed_agent_complete_condition_parity",
                ),
                ("smoke/full separation", "full_controller_68_calls_and_report"),
                ("smoke no automatic continuation", "preflight_modes_no_escalation"),
                ("interruption/incomplete", "interrupt_no_retry_and_custody"),
                ("no automatic resume", "storage_overwrite_and_identity"),
                ("immutable run storage", "storage_overwrite_and_identity"),
                ("report required fields", "full_controller_68_calls_and_report"),
                ("frozen schema unchanged", "frozen_pin_mismatch"),
                ("authority guards", "multi_and_mixed_no_repair"),
                ("no mutation/target authority", "architecture"),
                ("no discovery", "architecture"),
                ("historical revision-1 preserved", "architecture"),
            ]
            coverage.extend(
                [
                    (
                        "historical smoke artifacts unchanged",
                        "historical_artifacts_unchanged",
                    ),
                    (
                        "historical effect status unchanged",
                        "historical_artifacts_unchanged",
                    ),
                    (
                        "actual-provider revision and binding supplied",
                        "actual_composition_network_fenced",
                    ),
                    ("binding value is ollama", "actual_composition_network_fenced"),
                    (
                        "missing binding fails deterministically",
                        "actual_composition_network_fenced",
                    ),
                    (
                        "corrected composition passes model selection",
                        "actual_composition_network_fenced",
                    ),
                    (
                        "actual branch zero DNS socket HTTP under fence",
                        "actual_composition_network_fenced",
                    ),
                    ("attempt lifecycle representation", "never_attempted_partition"),
                    ("NEVER_ATTEMPTED", "never_attempted_partition"),
                    ("ATTEMPTED_NO_RESULT", "spawn_composition_failure_custody"),
                    ("COMPLETED_RESULT", "full_controller_68_calls_and_report"),
                    ("attempted accounting invariant", "never_attempted_partition"),
                    ("planned accounting invariant", "never_attempted_partition"),
                    (
                        "composition failure lifecycle",
                        "spawn_composition_failure_custody",
                    ),
                    ("timeout lifecycle", "timeout_lifecycle"),
                    ("invalid protocol lifecycle", "spawn_protocol_custody"),
                    (
                        "successful result lifecycle",
                        "spawn_replay_success_and_durable_diagnostics",
                    ),
                    (
                        "terminal-stop remaining slots never attempted",
                        "spawn_composition_failure_custody",
                    ),
                    ("safe child stages", "closed_diagnostics"),
                    ("safe failure categories", "closed_diagnostics"),
                    ("exception class safety", "closed_diagnostics"),
                    ("exit status distinct from envelope", "spawn_protocol_custody"),
                    ("IPC status custody", "spawn_protocol_custody"),
                    ("bounded cleanup action custody", "timeout_lifecycle"),
                    (
                        "dispatch marker semantics",
                        "spawn_replay_success_and_durable_diagnostics",
                    ),
                    (
                        "no false provider acceptance claim",
                        "spawn_composition_failure_custody",
                    ),
                    ("UNKNOWN effect preserved", "spawn_composition_failure_custody"),
                    (
                        "no raw exception message leakage",
                        "spawn_composition_failure_custody",
                    ),
                    (
                        "no prompt oracle secret diagnostic payload",
                        "spawn_protocol_custody",
                    ),
                    (
                        "Windows spawn live-composition regression",
                        "spawn_composition_failure_custody",
                    ),
                    ("process launch failure custody", "process_launch_failure"),
                    (
                        "semantic failures remain results",
                        "semantic_failure_remains_result",
                    ),
                    ("orphan finish rejected", "orphan_finish_rejected"),
                    (
                        "model versus semantic opportunity partition",
                        "full_controller_68_calls_and_report",
                    ),
                ]
            )
            parity = "invalid_output_classification_and_agent_parity"
            coverage.extend(
                [
                    (
                        "PARSER-DIAGNOSTICS-1: historical smoke 2 unchanged",
                        "historical_smoke2_unchanged_and_d13_cause_unknown",
                    ),
                    (
                        "d13 historical cause remains unknown (no backfill)",
                        "historical_smoke2_unchanged_and_d13_cause_unknown",
                    ),
                    (
                        "closed rejection and length taxonomies",
                        "closed_taxonomies_and_length_buckets",
                    ),
                    (
                        "Core output-contract classification",
                        "core_output_contract_classification",
                    ),
                    (
                        "ADR-021 document mirror parity",
                        "document_mirror_matches_adr021",
                    ),
                    ("non-JSON document", parity + "[prose_around_json]"),
                    ("malformed JSON", parity + "[malformed_json]"),
                    ("multiple JSON documents", parity + "[multiple_documents]"),
                    ("duplicate JSON key", parity + "[duplicate_key]"),
                    ("field-set failure", parity + "[missing_field]"),
                    ("field-type failure", parity + "[requests_type]"),
                    ("disposition failure", parity + "[invalid_disposition]"),
                    ("governing-source failure", parity + "[source_not_supplied]"),
                    ("request-set failure", parity + "[too_many_requests]"),
                    ("request-kind failure", parity + "[invalid_kind]"),
                    ("request-path failure", parity + "[named_without_path]"),
                    (
                        "request-choices failure",
                        parity + "[single_clarification_choice]",
                    ),
                    ("value-bound failure", parity + "[explanation_oversize]"),
                    ("coherence failure", parity + "[sufficient_with_request]"),
                    ("prerequisites classification", "prerequisites_classification"),
                    ("unknown fallback", "unknown_fallback_when_classifier_fails"),
                    ("disagreement behavior", "disagreement_keeps_agent_result"),
                    (
                        "valid output bypasses diagnostics",
                        "valid_output_bypasses_diagnostics",
                    ),
                    (
                        "Agent result authoritative; no semantic synthesis",
                        "disagreement_keeps_agent_result",
                    ),
                    (
                        "other failures not diagnosed",
                        "other_failures_and_success_are_not_diagnosed",
                    ),
                    (
                        "no raw output, prompt or exception text persisted",
                        "spawn_invalid_output_persists_closed_fields_only",
                    ),
                    (
                        "closed, consistent envelope diagnosis only",
                        "envelope_diagnosis_must_be_closed_and_consistent",
                    ),
                    (
                        "additive report fields; valid records unchanged",
                        "successful_call_records_have_no_output_fields",
                    ),
                    (
                        "smoke contract failure precedence unchanged",
                        "spawn_invalid_output_persists_closed_fields_only",
                    ),
                    ("no retry or second diagnostic call", parity),
                    (
                        "d09 semantic request-quality failure unchanged",
                        "d09_remains_semantic_request_quality_failure",
                    ),
                    (
                        "Agent, prompt, parser, revision-2 and profile pins unchanged",
                        "agent_evaluator_and_profile_sources_match_pins",
                    ),
                ]
            )
            offset = len(coverage) - 50
            for number, (label, case) in enumerate(coverage, 5):
                phase(number, label)
                if "test_" + case not in names:
                    raise ValueError("passing evidence missing: " + case)
                print("  verified in phase 4: " + case)
                done.append(current)
            tests(
                55 + offset,
                "revision-1 and revision-2 regressions",
                FORGE,
                "evaluation/tests/test_analyst_design_eval.py",
                "evaluation/tests/test_analyst_design_eval2.py",
            )
            tests(
                56 + offset,
                "sufficiency Agent regressions",
                ENG,
                "tests/test_sufficiency_agent.py",
            )
            tests(
                57 + offset,
                "evidence-loop regressions",
                FORGE,
                "evaluation/tests/test_analyst_evidence_loop.py",
            )
            tests(
                58 + offset,
                "RepositoryAnalyst regressions",
                ENG,
                "tests/test_analyst.py",
                "tests/test_json_document.py",
                "tests/test_analyst_prompt.py",
                "tests/test_analyst_sufficiency_prompt.py",
                "tests/test_analyst_sufficiency_semantics.py",
            )
            tests(
                59 + offset,
                "ForgeAI worker regressions",
                FORGE,
                "tests/test_worker.py",
                "tests/test_architecture.py",
            )
            tests(
                60 + offset,
                "architecture and governed Agent runtime",
                ROOT,
                "tests/unit/execution/test_agent.py",
                "tests/integration/composition/test_agent.py",
                "tests/architecture/test_agent.py",
            )
            phase(61 + offset, "validator cannot invoke live provider")
            if (
                env["FORGEAI_LIVE1_OFFLINE"] != "1"
                or "test_offline_live_provider_refused" not in names
            ):
                raise ValueError("offline fence missing")
            done.append(current)
            checked = [PACKAGE, TEST, FIX_TEST, DIAG_TEST, str(ROOT / SELF)]
            phase(62 + offset, "mypy")
            run(FORGE, "mypy", "--cache-dir", str(temp / "mypy"), *checked)
            done.append(current)
            phase(63 + offset, "Ruff lint")
            run(FORGE, "ruff", "check", "--no-cache", *checked)
            done.append(current)
            phase(64 + offset, "Ruff format")
            run(FORGE, "ruff", "format", "--check", "--no-cache", *checked)
            done.append(current)
            phase(65 + offset, "git diff check")
            git("diff", "--check", BASE)
            for name in ALLOWED:
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
        "FORGEAI-ANALYST-DESIGN-LIVE-1 PARSER-DIAGNOSTICS-1 LOCAL VALIDATION PASSED"
        " — no live model; no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
