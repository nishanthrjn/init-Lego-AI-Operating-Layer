r"""Offline qualification: uv run python .\validate_forgeai_analyst_sufficiency_safety_runtime_identity_2.py.

FORGEAI-ANALYST-SUFFICIENCY-SAFETY-RUNTIME-IDENTITY-2: forgeai-analyst-
sufficiency-safety-live/2 (Ollama 0.40.0 runtime identity revision). No model,
provider, Ollama or Docker. Passing authorizes neither PREFLIGHT nor BASELINE.
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
BASE = "ecbdf24526405fdc8edb00848294a0e9718cf995"  # refusal artifact committed
SELF = "validate_forgeai_analyst_sufficiency_safety_runtime_identity_2.py"
PACKAGE = "evaluation/analyst_sufficiency_safety_live2"
TEST = "evaluation/tests/test_analyst_sufficiency_safety_runtime_identity2.py"
PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-RUNTIME-IDENTITY-2.md"
LIVE1_PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-LIVE-1.md"
EVAL2_PLAN = "planning/FORGEAI-ANALYST-SUFFICIENCY-SAFETY-EVAL-2.md"
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
        "storage.py",
        "harness.py",
        "custody.py",
        "runtime-compat-2.json",
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
    "examples/forgeai/live1-preflight-411899d3f557",
    "examples/forgeai/live1-preflight-9bdb9f5867b6",
    "examples/forgeai/live1-preflight-a9e59b9f3773",
    "examples/forgeai/safety1-preflight-c80435f8dadc",
    "examples/forgeai/evaluation/analyst_design_eval1",
    "examples/forgeai/evaluation/analyst_design_eval2",
    "examples/forgeai/evaluation/analyst_evidence_loop",
    "examples/forgeai/evaluation/analyst_design_live1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval1",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_eval2",
    "examples/forgeai/evaluation/analyst_sufficiency_safety_live1",
    "examples/forgeai/evaluation/tests/test_analyst_sufficiency_safety_eval1.py",
    "examples/forgeai/evaluation/tests/test_analyst_sufficiency_safety_eval2.py",
    "examples/forgeai/evaluation/tests/test_analyst_sufficiency_safety_live1.py",
    "validate_forgeai_analyst_sufficiency_safety_live_1.py",
    LIVE1_PLAN,
    EVAL2_PLAN,
)
COVERAGE = [
    ("live/1 remains pinned to 0.35.1", "live1_remains_pinned_to_0_35_1"),
    ("live/1 remains immutable", "live1_remains_immutable"),
    ("live/2 identity is distinct", "live2_identity_is_distinct"),
    ("live/2 pins exactly 0.40.0", "live2_pins_exactly_0_40_0"),
    ("0.40.0 accepted by live/2", "0_40_0_accepted_by_live2"),
    ("0.35.1 rejected by live/2", "0_35_1_rejected_by_live2"),
    ("0.40.1 rejected", "arbitrary_newer_version_rejected[0.40.1]"),
    ("0.41.0 rejected", "arbitrary_newer_version_rejected[0.41.0]"),
    ("1.0.0 rejected", "arbitrary_newer_version_rejected[1.0.0]"),
    ("prefix 0.40 rejected", "arbitrary_newer_version_rejected[0.40]"),
    ("release candidate rejected", "arbitrary_newer_version_rejected[0.40.0-rc6]"),
    ("latest rejected", "arbitrary_newer_version_rejected[latest]"),
    ("model tag unchanged", "model_tag_unchanged"),
    ("model digest unchanged", "model_digest_unchanged"),
    ("SAFETY-EVAL-2 unchanged", "safety_eval2_unchanged"),
    ("Agent/prompt/parser unchanged", "agent_prompt_parser_unchanged"),
    ("membership unchanged", "membership_unchanged"),
    ("gates unchanged", "gates_unchanged"),
    ("budgets unchanged", "budgets_unchanged"),
    ("report semantics unchanged", "report_semantics_unchanged"),
    (
        "failed preflight artifact immutable",
        "failed_preflight_artifact_remains_immutable",
    ),
    ("refusal artifact recognized narrowly", "refusal_artifact_recognized_narrowly"),
    (
        "no arbitrary live artifact directory accepted",
        "no_arbitrary_live_artifact_directory_accepted",
    ),
    (
        "no semantic safety cases executed",
        "no_semantic_safety_cases_executed_by_validator",
    ),
    ("zero baseline calls", "zero_baseline_calls"),
]
SURFACES = {
    "GET /api/version",
    "GET /api/tags",
    "model identity and digest",
    "legacy GGUF compatibility migration (new in 0.40)",
    "POST /api/chat request fields",
    "POST /api/chat response fields",
    "non-streaming behavior",
    "error mapping",
    "timeout and cancellation",
    "UTF-8 / text handling",
    "default context length",
    "local endpoint behavior",
    "inference engine version",
}
CHECK = (
    "from analyst_design_live1.identity import git\n"
    "from analyst_sufficiency_safety_live1 import identity as one\n"
    "from analyst_sufficiency_safety_live2 import custody, identity as two\n"
    "a, b = one.binding(), two.binding()\n"
    "assert a['ollama_version'] == '0.35.1' and b['ollama_version'] == '0.40.0'\n"
    "assert b['condition'] == 'forgeai-analyst-sufficiency-safety-live/2'\n"
    "assert b['model_digest'] == a['model_digest'] == "
    "'sha256:9ec8897f747e246e970bc5cfdda85d22f1123dc2e3d34978a010a75968716849'\n"
    "same = ('frozen_digests', 'parser_identity', 'prompt_digest', "
    "'agent_fingerprint', 'membership', 'call_ceiling', 'call_seconds', "
    "'total_seconds', 'evaluation')\n"
    "assert all(a[k] == b[k] for k in same)\n"
    "record = two.compatibility()\n"
    "assert {s['surface'] for s in record['surfaces']} >= SURFACES\n"
    "custody.verify(git)\n"
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
    with tempfile.TemporaryDirectory(prefix="safety-runtime-identity2-") as directory:
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
            phase("qualification prerequisites and scope")
            for plan, marker in ((LIVE1_PLAN, "70/70"), (EVAL2_PLAN, "54/54")):
                text = (ROOT / plan).read_text(encoding="utf-8")
                if "LOCALLY QUALIFIED" not in text or marker not in text:
                    raise ValueError("qualification record missing: " + plan)
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
            phase(
                "frozen identities, exact 0.40.0 pin, compatibility evidence, "
                "run-artifact custody"
            )
            subprocess.run(
                [
                    "uv",
                    "run",
                    "--locked",
                    "--no-sync",
                    "python",
                    "-B",
                    "-c",
                    f"SURFACES = {SURFACES!r}\n" + CHECK,
                ],
                cwd=FORGE / "evaluation",
                env=env,
                check=True,
            )
            done.append(current)
            report = temp / "identity2.xml"
            tests(
                "offline runtime identity 2 tests",
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
                "LIVE-1 runtime regressions",
                FORGE,
                "evaluation/tests/test_analyst_design_live1.py",
                "evaluation/tests/test_analyst_design_live1_fix.py",
                "evaluation/tests/test_analyst_design_live1_diag.py",
            )
            tests(
                "sufficiency-Agent regressions", ENG, "tests/test_sufficiency_agent.py"
            )
            tests(
                "Ollama adapter and local-host regressions",
                ROOT,
                "tests/unit/reference/test_model.py",
                "tests/unit/reference/test_model_foundation.py",
                "tests/integration/composition/test_local_host.py",
                "tests/integration/composition/test_model_selection.py",
            )
            tests("ForgeAI Ollama binding regressions", FORGE, "tests/test_cli.py")
            tests(
                "architecture/import guards",
                ROOT,
                "tests/architecture/test_agent.py",
                "tests/architecture/test_import_boundaries.py",
            )
            phase("validator performs zero model/provider calls and no baseline")
            if (
                env["FORGEAI_LIVE1_OFFLINE"] != "1"
                or "test_no_semantic_safety_cases_executed_by_validator" not in names
                or "test_zero_baseline_calls" not in names
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
        "FORGEAI-ANALYST-SUFFICIENCY-SAFETY-RUNTIME-IDENTITY-2 LOCAL VALIDATION PASSED"
        " — offline; no model; no Docker; PREFLIGHT and BASELINE NOT authorized"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
