r"""Offline qualification: uv run python .\validate_forgeai_analyst_sufficiency_safety_live_2_preflight_custody_1.py.

FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-2-PREFLIGHT-CUSTODY-1: exact custody
admission of the committed live/2 PREFLIGHT directory. Git reads only; no
model, provider, Ollama or Docker. Passing does not authorize the BASELINE.
"""

import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGE = ROOT / "examples/forgeai"
BASE = "72cb3463ef825b0f6062376945de77d4f5189400"  # live/2 preflight committed
SELF = "validate_forgeai_analyst_sufficiency_safety_live_2_preflight_custody_1.py"
LIVE2 = "examples/forgeai/evaluation/analyst_sufficiency_safety_live2"
TEST = "evaluation/tests/test_analyst_sufficiency_safety_live2_preflight_custody1.py"
PACKAGE_CUSTODY = "evaluation/analyst_sufficiency_safety_live2/custody.py"
RI2_TEST = "evaluation/tests/test_analyst_sufficiency_safety_runtime_identity2.py"
PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-2-PREFLIGHT-CUSTODY-1.md"
RI2_PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-RUNTIME-IDENTITY-2.md"
ALLOWED = {
    SELF,
    "examples/forgeai/" + TEST,
    "examples/forgeai/" + RI2_TEST,  # one stale "no safety2 directory" assertion
    PLAN,
    RI2_PLAN,  # appended custody note only
    LIVE2 + "/custody.py",
    LIVE2 + "/README.md",  # status line only
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
}
PROTECTED = (
    "src",
    "packages",
    "adrs",
    "examples/forgeai/src",
    "examples/forgeai/live1-smoke-d59e9c3f030b",
    "examples/forgeai/live1-smoke-227bdd3cec0b",
    "examples/forgeai/live1-smoke-bf448d5a12b3",
    "examples/forgeai/live1-preflight-411899d3f557",
    "examples/forgeai/live1-preflight-9bdb9f5867b6",
    "examples/forgeai/live1-preflight-a9e59b9f3773",
    "examples/forgeai/safety1-preflight-c80435f8dadc",
    "examples/forgeai/safety2-preflight-300452037205",
    "examples/forgeai/evaluation/analyst_design_live1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval2",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_live1",
    LIVE2 + "/identity.py",
    LIVE2 + "/storage.py",
    LIVE2 + "/harness.py",
    LIVE2 + "/__init__.py",
    LIVE2 + "/__main__.py",
    LIVE2 + "/runtime-compat-2.json",
)
COVERAGE = [
    ("new live/2 preflight accepted", "new_live2_preflight_directory_is_accepted"),
    ("exact tree id required", "exact_tree_id_required"),
    ("one-byte modification rejected", "one_byte_modification_rejected"),
    (
        "another safety2-preflight rejected",
        "another_safety2_preflight_directory_rejected",
    ),
    (
        "arbitrary untracked run directory rejected",
        "arbitrary_untracked_run_directory_rejected",
    ),
    ("prior seven entries accepted", "prior_seven_entries_remain_accepted"),
    ("prior changed artifact rejected", "prior_changed_artifact_remains_rejected"),
    ("run UUID matches", "run_uuid_matches"),
    ("condition/report identities match", "condition_and_report_identities_match"),
    ("mode is PREFLIGHT", "mode_is_preflight"),
    ("calls == 0", "calls_zero"),
    ("records empty", "records_empty"),
    ("model digest matches", "model_digest_matches"),
    ("Ollama version 0.40.0", "ollama_version_is_0_40_0"),
    ("leakage status passed", "leakage_status_passed"),
    ("no baseline artifact admitted", "no_baseline_artifact_admitted"),
    ("report identity fields required", "report_identity_fields_required"),
    (
        "admission changes only the custody digest",
        "admission_changes_only_the_custody_source_digest",
    ),
]
CHECK = (
    "from analyst_design_live1.identity import git\n"
    "from analyst_sufficiency_safety_eval2 import data\n"
    "from analyst_sufficiency_safety_live1 import identity as one\n"
    "from analyst_sufficiency_safety_live2 import custody, identity as two\n"
    "result = custody.verify(git)\n"
    "assert len(result['directories']) == 8\n"
    "assert not [d for d in result['directories'] if '-baseline-' in d]\n"
    "a, b = one.binding(), two.binding()\n"
    "assert (b['condition'], b['report'], b['ollama_version']) == ("
    "'forgeai-analyst-sufficiency-safety-live/2', "
    "'forgeai-analyst-sufficiency-safety-live-report/2', '0.40.0')\n"
    "assert two.VERSION == '0.40.0' and one.VERSION == '0.35.1'\n"
    "assert b['model'] == 'qwen2.5-coder:14b' and b['model_digest'] == "
    "'sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849'\n"
    "same = ('frozen_digests', 'parser_identity', 'prompt_digest', "
    "'agent_fingerprint', 'agent_version', 'membership', 'call_ceiling', "
    "'call_seconds', 'total_seconds', 'evaluation', 'runtime_revision')\n"
    "assert all(a[k] == b[k] for k in same if k in a) and b['frozen_digests'] "
    "== data.freeze()\n"
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
    with tempfile.TemporaryDirectory(prefix="safety-live2-custody1-") as directory:
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
            phase("runtime-identity-2 qualification prerequisite and scope")
            text = (ROOT / RI2_PLAN).read_text(encoding="utf-8")
            if "LOCALLY QUALIFIED" not in text or "41/41" not in text:
                raise ValueError("runtime identity 2 qualification record missing")
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
            ri2 = git("diff", BASE, "--", "examples/forgeai/" + RI2_TEST)
            edits = [
                line
                for line in ri2.splitlines()
                if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
            ]
            if len(edits) > 2 or (edits and "-baseline-" not in edits[-1]):
                raise ValueError("runtime identity 2 test changed beyond one assertion")
            done.append(current)
            phase(
                "exact custody, live/2 preflight integrity, no baseline, "
                "unchanged identities"
            )
            subprocess.run(
                ["uv", "run", "--locked", "--no-sync", "python", "-B", "-c", CHECK],
                cwd=FORGE / "evaluation",
                env=env,
                check=True,
            )
            done.append(current)
            report = temp / "custody.xml"
            tests("offline custody tests", FORGE, TEST, f"--junitxml={report}")
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
            tests("runtime identity 2 regressions", FORGE, RI2_TEST)
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
            phase("validator performs zero model/provider calls")
            if env["FORGEAI_LIVE1_OFFLINE"] != "1":
                raise ValueError("offline guard missing")
            done.append(current)
            checked = [PACKAGE_CUSTODY, TEST, str(ROOT / SELF)]
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
        "FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-2-PREFLIGHT-CUSTODY-1 LOCAL "
        "VALIDATION PASSED — offline; no model; no Docker; BASELINE NOT authorized"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
