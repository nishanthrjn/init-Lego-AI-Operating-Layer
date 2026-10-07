r"""Offline operator qualification: uv run python .\validate_forgeai_analyst_design_live_1.py."""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
ENG = ROOT / "packages/legoai-engineering"
BASE = "a9aaabe154f3afa00cbf4ada1c70e3e378233eac"
PACKAGE = "evaluation/analyst_design_live1"
TEST = "evaluation/tests/test_analyst_design_live1.py"
SELF = "validate_forgeai_analyst_design_live_1.py"
ALLOWED = {
    SELF,
    "examples/forgeai/" + TEST,
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
} | {
    "examples/forgeai/" + PACKAGE + "/" + name
    for name in (
        "__init__.py",
        "__main__.py",
        "identity.py",
        "runtime.py",
        "sequence.py",
        "measurement.py",
        "storage.py",
        "harness.py",
        "pins.json",
        "report-schema.json",
        "README.md",
    )
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
            if changed - ALLOWED:
                raise ValueError("unexpected files: " + repr(sorted(changed - ALLOWED)))
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
                4, "offline harness qualification", FORGE, TEST, f"--junitxml={report}"
            )
            cases = list(ET.parse(report).getroot().iter("testcase"))
            if not cases or any(list(c) for c in cases):
                raise ValueError("no failed/skipped qualification cases allowed")
            names = {c.attrib["name"].split("[")[0] for c in cases}
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
            for number, (label, case) in enumerate(coverage, 5):
                phase(number, label)
                if "test_" + case not in names:
                    raise ValueError("passing evidence missing: " + case)
                print("  verified in phase 4: " + case)
                done.append(current)
            tests(
                55,
                "revision-1 and revision-2 regressions",
                FORGE,
                "evaluation/tests/test_analyst_design_eval.py",
                "evaluation/tests/test_analyst_design_eval2.py",
            )
            tests(
                56,
                "sufficiency Agent regressions",
                ENG,
                "tests/test_sufficiency_agent.py",
            )
            tests(
                57,
                "evidence-loop regressions",
                FORGE,
                "evaluation/tests/test_analyst_evidence_loop.py",
            )
            tests(
                58,
                "RepositoryAnalyst regressions",
                ENG,
                "tests/test_analyst.py",
                "tests/test_json_document.py",
                "tests/test_analyst_prompt.py",
                "tests/test_analyst_sufficiency_prompt.py",
                "tests/test_analyst_sufficiency_semantics.py",
            )
            tests(
                59,
                "ForgeAI worker regressions",
                FORGE,
                "tests/test_worker.py",
                "tests/test_architecture.py",
            )
            tests(
                60,
                "architecture and governed Agent runtime",
                ROOT,
                "tests/unit/execution/test_agent.py",
                "tests/integration/composition/test_agent.py",
                "tests/architecture/test_agent.py",
            )
            phase(61, "validator cannot invoke live provider")
            if (
                env["FORGEAI_LIVE1_OFFLINE"] != "1"
                or "test_offline_live_provider_refused" not in names
            ):
                raise ValueError("offline fence missing")
            done.append(current)
            checked = [PACKAGE, TEST, str(ROOT / SELF)]
            phase(62, "mypy")
            run(FORGE, "mypy", "--cache-dir", str(temp / "mypy"), *checked)
            done.append(current)
            phase(63, "Ruff lint")
            run(FORGE, "ruff", "check", "--no-cache", *checked)
            done.append(current)
            phase(64, "Ruff format")
            run(FORGE, "ruff", "format", "--check", "--no-cache", *checked)
            done.append(current)
            phase(65, "git diff check")
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
        "FORGEAI-ANALYST-DESIGN-LIVE-1 HARNESS LOCAL VALIDATION PASSED — no live model; no Docker"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
