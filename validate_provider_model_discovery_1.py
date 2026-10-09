r"""Offline qualification: uv run python .\validate_provider_model_discovery_1.py.

PROVIDER-MODEL-DISCOVERY-1 (ADR-024 §22): one explicitly operator-authorized,
provider-neutral credentialed model-discovery operation over the existing
SRCP-1 HTTPS path. Its own ProviderDiscoveryAdmission, a durable INTENDED
provider-control attempt, a per-call Secret use, T2 `POST {root}/models` with
an empty body and a bounded id-only parser; no disclosure, retry, fallback or
routing. Only process-local synthetic TLS servers with test-only certificates
and synthetic S1 material are used: no external network, provider or KISSKI.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_secret_use_durable_custody_1 import IMPLEMENTATION_TEST_DIRECTORIES

ROOT = Path(__file__).resolve().parent
BASE = "4281781"  # OPENAI-COMPATIBLE-REMOTE-1 qualified; last commit before this
PRODUCTION = (
    "src/legoai/governance/provider_control.py",
    "src/legoai/reference/_credential_https.py",
    "src/legoai/reference/_remote_attempts.py",
    "src/legoai/reference/model_openai_compatible.py",
    "src/legoai/runtime/_composition/provider_discovery.py",
    "src/legoai/runtime/_composition/remote_model.py",
)
FLOW = "tests/integration/composition/test_provider_discovery.py"
VALUES = "tests/unit/governance/test_provider_control.py"
PARSER = "tests/unit/reference/test_model_list.py"
ARCH = "tests/architecture/test_provider_discovery.py"
TESTS = (
    FLOW,
    VALUES,
    PARSER,
    ARCH,
    "tests/support/provider_discovery.py",
    "tests/architecture/test_credential_https.py",
    "tests/architecture/test_import_boundaries.py",
    "tests/architecture/test_openai_compatible_remote.py",
    "tests/architecture/test_remote_attempts.py",
    "tests/architecture/test_remote_disclosure.py",
)
SELF = "validate_provider_model_discovery_1.py"
PYTHON_FILES = (*PRODUCTION, *TESTS, SELF)
ALLOWED = set(PYTHON_FILES) | {
    "adrs/ADR-024.md",
    "docs/model-composition.md",
    "docs/secret-ref-1a.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
}
# Pre-existing stale wheel manifest (predates T2); not this slice.
STALE = "tests/architecture/test_package_install.py::test_build_and_fresh_wheel"


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
            *(f":(exclude){name}/**" for name in IMPLEMENTATION_TEST_DIRECTORIES),
        ).splitlines()
    )
    if changed - ALLOWED:
        raise RuntimeError("unexpected scope: " + repr(sorted(changed - ALLOWED)))


def main() -> int:
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.update(UV_OFFLINE="1", PYTHONDONTWRITEBYTECODE="1")
    completed: list[str] = []
    phase = "1 scope guard (no ForgeAI, ModelPort, KISSKI or ComfyUI change)"
    cache = ROOT / ".pytest_cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="model-discovery-1-", dir=cache) as tmp:
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
            tests("2 provider-control admission values and pure evaluator", VALUES)
            tests("3 bounded model-list parser and the fixed /models target", PARSER)
            focused(
                4,
                "governed POST /models: listed, malformed, rejected, unknown, TLS",
                FLOW,
                "test_listed_models_through_the_governed_path",
                "test_empty_listing_is_listed_with_no_models",
                "test_malformed_listing_keeps_completed_transport_truth",
                "test_complete_rejections_are_never_retried",
                "test_incomplete_responses_are_unknown",
                "test_tls_failure_is_not_sent_without_realization",
            )
            focused(
                5,
                "authority separation and admission refusals reach nothing",
                FLOW,
                "test_no_admission_reaches_nothing",
                "test_a_disclosure_admission_never_authorizes_discovery",
                "test_a_discovery_admission_never_authorizes_disclosure",
                "test_admission_mismatch_reaches_nothing",
                "test_other_credential_revision_reaches_nothing",
                "test_operation_is_typed_and_fixed",
            )
            focused(
                6,
                "Secret purpose, consumer, currentness, margin; INTENDED first",
                FLOW,
                "test_model_bearer_credential_purpose_reaches_nothing",
                "test_wrong_secret_consumer_is_refused_before_transport",
                "test_stale_secret_authority_is_refused_before_transport",
                "test_less_than_the_margin_refuses_inside_the_domain",
                "test_intended_failure_reaches_no_secret_or_network",
            )
            focused(
                7,
                "no widening, one request per call, ambient inputs and canaries",
                FLOW,
                "test_result_cannot_widen_authority_or_change_configuration",
                "test_each_call_is_one_attempt_one_use_one_request",
                "test_ambient_keys_and_task_content_never_enter_the_request",
                "test_endpoint_requires_a_secret_reference",
            )
            tests("8 all discovery tests and boundaries", FLOW, VALUES, PARSER, ARCH)
            tests(
                "9 ownership and import boundaries",
                "tests/architecture",
                "--deselect",
                STALE,
            )
            tests(
                "10 REMOTE OpenAI-compatible chat/embedding regressions",
                "tests/integration/composition/test_openai_compatible_remote.py",
                "tests/integration/composition/test_secret_uses.py",
                "tests/unit/reference/test_openai_compatible_exchange.py",
            )
            tests(
                "11 T2, attempt custody, S1, disclosure and Secret regressions",
                "tests/unit/reference/test_credential_https.py",
                "tests/integration/composition/test_credential_https_exchange.py",
                "tests/unit/reference/test_remote_attempts.py",
                "tests/integration/composition/test_remote_attempt_custody.py",
                "tests/unit/reference/test_secret_source_s1.py",
                "tests/unit/reference/test_secret_ref.py",
                "tests/unit/reference/test_secret_durable_custody.py",
                "tests/integration/composition/test_remote_disclosure_gate.py",
                "tests/integration/composition/test_remote_disclosure.py",
                "tests/unit/governance/test_disclosure.py",
            )
            tests(
                "12 OpenAI-compatible LOCAL, Ollama, Model and Agent regressions",
                "tests/unit/reference/test_openai_compatible.py",
                "tests/integration/composition/test_openai_compatible.py",
                "tests/unit/reference/test_model.py",
                "tests/integration/composition/test_local_host.py",
                "tests/integration/composition/test_model_governed.py",
                "tests/integration/composition/test_agent.py",
            )
            tests(
                "13 Core unit, integration and contract regressions",
                "tests/unit",
                "tests/integration",
                "tests/contract",
            )
            tests(
                "14 DocuMind regressions",
                "tests/unit",
                "tests/integration",
                cwd=ROOT / "examples/documind",
            )
            tests(
                "15 ForgeAI regressions",
                "tests/test_architecture.py",
                "tests/test_worker.py",
                "tests/test_review.py",
                "tests/test_rework.py",
                cwd=ROOT / "examples/forgeai",
            )
            run(
                "16 mypy",
                [
                    "mypy",
                    "--cache-dir",
                    str(temp / "mypy"),
                    "src",
                    FLOW,
                    VALUES,
                    PARSER,
                    ARCH,
                    "tests/support/provider_discovery.py",
                    str(Path(__file__).resolve()),
                ],
            )
            run("17 Ruff lint", ["ruff", "check", "--no-cache", *PYTHON_FILES])
            run(
                "18 Ruff format",
                ["ruff", "format", "--check", "--no-cache", *PYTHON_FILES],
            )
            phase = "19 git diff check"
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
        "PROVIDER-MODEL-DISCOVERY-1 LOCAL VALIDATION PASSED - offline; synthetic "
        "local TLS and S1 material only; no external network, provider, KISSKI, "
        "retry, fallback or routing"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
