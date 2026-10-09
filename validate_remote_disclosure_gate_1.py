r"""Offline ADR-024 qualification: uv run python .\validate_remote_disclosure_gate_1.py.

REMOTE-DISCLOSURE-GATE-1: the host-side declaration carrier, the
invocation-time disclosure gate before provider work, safe refusal mapping and
typed disclosure Evidence. Exercised through a bounded internal seam; REMOTE
stays refused at open. No provider, network, Docker or credential is used.
Existing installed project environments are required; never syncs.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "fd1e05a"  # governance slice qualified; last commit before this slice
PRODUCTION = (
    "src/legoai/governance/disclosure.py",
    "src/legoai/evidence/ports.py",
    "src/legoai/runtime/api.py",
    "src/legoai/runtime/local.py",
    "src/legoai/runtime/_composition/disclosure.py",
    "src/legoai/runtime/_composition/model_governed.py",
    "src/legoai/runtime/_composition/agent.py",
)
TESTS = (
    "tests/unit/governance/test_disclosure.py",
    "tests/integration/composition/test_remote_disclosure_gate.py",
    "tests/architecture/test_remote_disclosure.py",
    "tests/architecture/test_import_boundaries.py",
    "tests/architecture/test_agent.py",
)
SELF = "validate_remote_disclosure_gate_1.py"
PYTHON_FILES = (*PRODUCTION, *TESTS, SELF)
ALLOWED = set(PYTHON_FILES) | {
    "docs/model-composition.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
}
UNIT = "tests/unit/governance/test_disclosure.py"
GATE = "tests/integration/composition/test_remote_disclosure_gate.py"
HOST = "tests/integration/composition/test_remote_disclosure.py"
ARCH = "tests/architecture/test_remote_disclosure.py"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, encoding="utf-8", check=True
    ).stdout


def scope() -> None:
    changed = set(git("diff", "--name-only", BASE).splitlines())
    changed.update(
        git(
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            ".",
            ":(exclude)examples/forgeai/.lq13-test-temp/**",
            ":(exclude)examples/forgeai/aq1q-r4-qwen2.5-coder-14b/**",
        ).splitlines()
    )
    if changed - ALLOWED:
        raise RuntimeError("unexpected scope: " + repr(sorted(changed - ALLOWED)))


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(UV_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
    completed: list[str] = []
    phase = "1 scope guard (no adapter, ForgeAI or Engineering change)"
    cache = ROOT / ".pytest_cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="disclosure-gate-", dir=cache) as tmp:
        temp = Path(tmp)

        def run(name: str, args: list[str], cwd: Path = ROOT) -> None:
            nonlocal phase
            phase = name
            print("[PHASE] " + phase, flush=True)
            command = (
                [sys.executable, "-B", "-m"]
                if cwd == ROOT
                else [
                    "uv",
                    "run",
                    "--locked",
                    "--no-sync",
                    "--offline",
                    "python",
                    "-B",
                    "-m",
                ]
            )
            subprocess.run([*command, *args], cwd=cwd, env=env, check=True)
            completed.append(name)

        def tests(name: str, *selectors: str, cwd: Path = ROOT) -> None:
            run(
                name,
                [
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    "--basetemp",
                    str(temp / name.split()[0]),
                    *selectors,
                ],
                cwd,
            )

        def focused(number: int, name: str, file: str, *names: str) -> None:
            tests(f"{number} {name}", *(file + "::" + n for n in names))

        try:
            print("[PHASE] " + phase, flush=True)
            scope()
            completed.append(phase)
            focused(
                2,
                "refusal matrix before any provider work",
                GATE,
                "test_refusals_happen_before_any_provider_work",
                "test_repository_classes_cannot_be_declared_without_a_repository",
                "test_purpose_mismatch_chat_admission_cannot_authorize_embedding",
                "test_human_access_condition_respected",
            )
            focused(
                3,
                "chat, embedding and Agent paths share one gate",
                GATE,
                "test_agent_runtime_path_is_gated_too",
                "test_admitted_chat_reaches_the_provider_with_the_exact_request",
                "test_admitted_embedding_uses_the_same_gate",
            )
            focused(
                4,
                "SYNTHETIC probe and DERIVED_DIAGNOSTIC lineage",
                GATE,
                "test_synthetic_probe_admitted_with_permitted_unknown_facts",
                "test_unknown_processor_identity_refuses_even_synthetic",
                "test_derived_diagnostic_respects_evaluator_lineage",
            )
            focused(
                5,
                "no widening and execution binding",
                GATE,
                "test_model_output_and_content_cannot_add_classes",
                "test_provider_response_and_evidence_never_alter_admission",
                "test_one_execution_cannot_borrow_another_executions_declaration",
                "test_forged_context_is_rejected_before_the_gate",
                "test_declaration_is_immutable_and_bound_at_minting",
                "test_check_content_cannot_invent_a_repository_identity",
            )
            focused(
                6,
                "safe disclosure Evidence and custody failures",
                GATE,
                "test_evidence_contains_only_safe_facts",
                "test_repository_recorded_only_when_applicable",
                "test_refusal_evidence_custody_failure_still_settles_none",
                "test_admitted_evidence_custody_failure_preserves_the_outcome",
                "test_admitted_preflight_failure_records_nothing_sent",
            )
            focused(
                7,
                "cancellation",
                GATE,
                "test_cancellation_inside_the_gate_never_reaches_the_provider",
                "test_cancellation_during_an_admitted_call_is_attributed_unknown",
            )
            focused(
                8,
                "LOCAL unchanged and REMOTE still refused",
                GATE,
                "test_local_host_without_a_gate_ignores_declarations",
                "test_remote_selection_is_still_refused_at_open",
            )
            tests("9 all gate tests", GATE)
            tests("10 disclosure governance regressions", UNIT, HOST)
            tests(
                "11 ownership and import boundaries",
                ARCH,
                "tests/architecture/test_import_boundaries.py",
                "tests/architecture/test_local_host.py",
                "tests/architecture/test_agent.py",
                "tests/architecture/test_openai_compatible.py",
            )
            tests(
                "12 governed Model, runtime, OpenAI-compatible and Ollama",
                "tests/integration/composition/test_model_governed.py",
                "tests/integration/composition/test_local_host.py",
                "tests/integration/composition/test_model_selection.py",
                "tests/integration/composition/test_openai_compatible.py",
                "tests/unit/reference/test_openai_compatible.py",
                "tests/unit/reference/test_model.py",
            )
            tests(
                "13 Evidence and Agent regressions",
                "tests/unit/evidence",
                "tests/unit/execution/test_agent.py",
                "tests/integration/composition/test_agent.py",
            )
            tests(
                "14 Core unit, integration and contract regressions",
                "tests/unit",
                "tests/integration",
                "tests/contract",
            )
            tests(
                "15 DocuMind regressions",
                "tests/unit",
                "tests/integration",
                cwd=ROOT / "examples/documind",
            )
            tests(
                "16 ForgeAI regressions",
                "tests/test_architecture.py",
                "tests/test_worker.py",
                "tests/test_review.py",
                "tests/test_rework.py",
                cwd=ROOT / "examples/forgeai",
            )
            run(
                "17 mypy",
                [
                    "mypy",
                    "--cache-dir",
                    str(temp / "mypy"),
                    "src",
                    UNIT,
                    GATE,
                    HOST,
                    ARCH,
                    str(Path(__file__).resolve()),
                ],
            )
            run("18 Ruff lint", ["ruff", "check", "--no-cache", *PYTHON_FILES])
            run(
                "19 Ruff format",
                ["ruff", "format", "--check", "--no-cache", *PYTHON_FILES],
            )
            phase = "20 git diff check"
            print("[PHASE] " + phase, flush=True)
            git("diff", "--check", BASE)
            completed.append(phase)
        except (subprocess.CalledProcessError, RuntimeError, OSError) as error:
            for name in completed:
                print("PASS " + name)
            print("FAIL " + phase + ": " + str(error))
            return 1
    for name in completed:
        print("PASS " + name)
    print(
        "REMOTE-DISCLOSURE-GATE-1 LOCAL VALIDATION PASSED - offline; internal "
        "seam only; REMOTE still refused; no provider, network or credential"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
