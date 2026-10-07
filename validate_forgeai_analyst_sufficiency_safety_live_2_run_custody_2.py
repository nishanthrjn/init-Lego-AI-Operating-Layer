r"""Offline qualification: uv run python .\validate_forgeai_analyst_sufficiency_safety_live_2_run_custody_2.py.

FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-2-RUN-CUSTODY-2: exact custody of the
first live/2 BASELINE and two retained zero-call PREFLIGHTs. Git reads only:
no model, provider, Ollama or Docker. Passing authorizes no live run.
"""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
BASE = "9a56a0d"  # SAFETY-EVAL-3 qualification recorded
SELF = "validate_forgeai_analyst_sufficiency_safety_live_2_run_custody_2.py"
CUSTODY = "evaluation/analyst_sufficiency_safety_live2/custody.py"
TEST = "evaluation/tests/test_analyst_sufficiency_safety_live2_run_custody2.py"
PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-2-RUN-CUSTODY-2.md"
EVAL3_PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-EVAL-3.md"
ALLOWED = {
    SELF,
    "examples/forgeai/" + CUSTODY,
    "examples/forgeai/" + TEST,
    PLAN,
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
}
PROTECTED = (
    ".gitignore",
    "src",
    "packages",
    "adrs",
    "examples/forgeai/src",
    "examples/forgeai/evaluation/analyst_design_live1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval2",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval3",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_live1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_live2/identity.py",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_live2/storage.py",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_live2/harness.py",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_live2/runtime-compat-2.json",
    "examples/forgeai/evaluation/safety2-preflight-20261007-01",
    "examples/forgeai/evaluation/safety2-preflight-20261007-a",
    "examples/forgeai/safety2-baseline-3cf8aba9a377",
    "examples/forgeai/safety2-preflight-300452037205",
    "examples/forgeai/safety1-preflight-c80435f8dadc",
    "examples/forgeai/live1-smoke-d59e9c3f030b",
    "examples/forgeai/live1-smoke-227bdd3cec0b",
    "examples/forgeai/live1-smoke-bf448d5a12b3",
    "examples/forgeai/evaluation/tests/test_analyst_sufficiency_safety_live2_preflight_custody1.py",
    "examples/forgeai/evaluation/tests/test_analyst_sufficiency_safety_runtime_identity2.py",
)
# Qualified assertions whose facts this slice changes by design. They are
# deselected by exact id (never edited); every other test in their suites runs.
SUPERSEDED = {
    "evaluation/tests/test_analyst_sufficiency_safety_live2_preflight_custody1.py"
    "::test_prior_seven_entries_remain_accepted": "asserted exactly 8 pins; now 11",
    "evaluation/tests/test_analyst_sufficiency_safety_live2_preflight_custody1.py"
    "::test_no_baseline_artifact_admitted": "asserted no baseline pin; baseline admitted",
    "evaluation/tests/test_analyst_sufficiency_safety_runtime_identity2.py"
    "::test_zero_baseline_calls": "asserted no baseline directory; baseline exists",
}
COVERAGE = [
    ("baseline directory admitted", "baseline_directory_admitted"),
    ("baseline exact tree required", "baseline_exact_tree_required"),
    ("one-byte baseline change rejected", "one_byte_baseline_change_rejected"),
    ("extra baseline file rejected", "extra_baseline_file_rejected"),
    ("baseline run UUID checked", "baseline_run_uuid_checked"),
    ("baseline mode checked", "baseline_mode_checked"),
    ("baseline decision G checked", "baseline_decision_g_checked"),
    ("baseline completeness checked", "baseline_completeness_checked"),
    ("baseline authority count checked", "baseline_authority_count_checked"),
    (
        "baseline critical progression count checked",
        "baseline_critical_progression_count_checked",
    ),
    ("baseline zero retry recorded", "baseline_no_retry_recorded"),
    ("baseline report fields checked", "baseline_report_fields_checked"),
    ("first nested preflight admitted", "first_retained_preflight_admitted"),
    ("second nested preflight admitted", "second_retained_preflight_admitted"),
    ("each nested preflight own tree", "each_nested_preflight_has_own_tree"),
    ("mutated nested preflight rejected", "mutated_nested_preflight_rejected"),
    (
        "arbitrary nested run directory rejected",
        "arbitrary_nested_run_directory_rejected",
    ),
    (
        "arbitrary top-level baseline rejected",
        "arbitrary_top_level_baseline_rejected",
    ),
    ("wildcard admission absent", "wildcard_admission_absent"),
    ("existing historical pins unchanged", "existing_historical_pins_unchanged"),
    (
        "original live/2 preflight still accepted",
        "successful_original_live2_preflight_still_accepted",
    ),
    ("live/1 refusal still accepted", "live1_refusal_still_accepted"),
    ("ignored live evidence rejected", "ignored_live_evidence_rejected"),
    (
        "committed/working-tree mismatch rejected",
        "committed_working_tree_mismatch_rejected",
    ),
    ("SAFETY-EVAL-3 unchanged", "safety_eval3_unchanged"),
    ("SAFETY-EVAL-2 unchanged", "safety_eval2_unchanged"),
    ("live/2 semantic identity unchanged", "live2_semantic_identity_unchanged"),
    ("zero provider/model calls", "zero_provider_model_calls"),
    ("no baseline rerun", "no_baseline_rerun"),
    ("no evaluator run", "no_evaluator_run"),
]
CHECK = (
    "from analyst_design_live1.identity import git\n"
    "from analyst_sufficiency_safety_eval2 import data as d2\n"
    "from analyst_sufficiency_safety_eval3 import data as d3\n"
    "from analyst_sufficiency_safety_live2 import custody\n"
    "d2.freeze(); d3.freeze()\n"
    "r = custody.verify(git)\n"
    "assert len(r['directories']) == 11, r['directories']\n"
    "assert not custody.ignored_run_directories(git)\n"
)


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
    with tempfile.TemporaryDirectory(prefix="safety-live2-custody2-") as directory:
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
            deselect = [
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
                *deselect,
                *targets,
            )
            done.append(current)

        try:
            phase("SAFETY-EVAL-3 qualification prerequisite and scope")
            text = (ROOT / EVAL3_PLAN).read_text(encoding="utf-8")
            if "LOCALLY QUALIFIED" not in text or "81/81" not in text:
                raise ValueError("SAFETY-EVAL-3 qualification record missing")
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
            phase(".gitignore hides no live run evidence")
            ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
            if "safety2-baseline" in ignore or "safety2-preflight" in ignore:
                raise ValueError("ignore rule for live run evidence")
            done.append(current)
            phase("exact custody of 11 run directories; frozen evaluators")
            subprocess.run(
                ["uv", "run", "--locked", "--no-sync", "python", "-B", "-c", CHECK],
                cwd=FORGE / "evaluation",
                env=env,
                check=True,
            )
            done.append(current)
            report = temp / "custody2.xml"
            tests("offline custody-2 tests", FORGE, TEST, f"--junitxml={report}")
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
                "preflight-custody-1 regressions (superseded counts deselected)",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_live2_preflight_custody1.py",
            )
            tests(
                "runtime-identity-2 regressions (superseded check deselected)",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_runtime_identity2.py",
            )
            tests(
                "SAFETY-LIVE-1 harness regressions",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_live1.py",
            )
            tests(
                "SAFETY-EVAL-2 regressions",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_eval2.py",
            )
            tests(
                "SAFETY-EVAL-3 regressions (sealed; offline scorer only)",
                FORGE,
                "evaluation/tests/test_analyst_sufficiency_safety_eval3.py",
            )
            phase("validator performs zero model/provider calls")
            if (
                env["FORGEAI_LIVE1_OFFLINE"] != "1"
                or "test_zero_provider_model_calls" not in names
            ):
                raise ValueError("offline guard missing")
            done.append(current)
            checked = [CUSTODY, TEST, str(ROOT / SELF)]
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
        "FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-2-RUN-CUSTODY-2 LOCAL VALIDATION "
        "PASSED — offline; no model; no Docker; no live run authorized"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
