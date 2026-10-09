r"""Offline qualification: uv run python .\validate_credential_https_t2.py.

CREDENTIAL-HTTPS-T2: the private SRCP-1 credential-bearing HTTPS transport.
Verified TLS before Secret realization; every credential-bearing nonblocking
write is currentness-gated under the shared ordering domain after a durable
INTENDED attempt claim; bounded observations keep NONE/UNKNOWN/completed
effect truth; no retry, redirect, proxy or fallback. Only a process-local
synthetic TLS server with test-only certificates is contacted; no external
network, provider or KISSKI. REMOTE stays refused. Wall-clock expiry at the
handoff is detected after the fact, not prevented (ADR-023 SRCP-1).
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_secret_use_durable_custody_1 import IMPLEMENTATION_TEST_DIRECTORIES

ROOT = Path(__file__).resolve().parent
BASE = "1b2d69e"  # attempt custody qualified; last commit before this slice
PRODUCTION = (
    "src/legoai/reference/_credential_https.py",
    "src/legoai/reference/secret.py",
    "src/legoai/runtime/_composition/secret.py",
    "src/legoai/runtime/_composition/credential_https.py",
)
TESTS = (
    "tests/unit/reference/test_credential_https.py",
    "tests/integration/composition/test_credential_https_exchange.py",
    "tests/architecture/test_credential_https.py",
    "tests/architecture/test_import_boundaries.py",
    "tests/architecture/test_remote_disclosure.py",
    "tests/architecture/test_remote_attempts.py",
    "tests/support/tls_server.py",
)
SELF = "validate_credential_https_t2.py"
PYTHON_FILES = (*PRODUCTION, *TESTS, SELF)
ALLOWED = set(PYTHON_FILES) | {
    "tests/support/tls/test-ca.pem",
    "tests/support/tls/localhost.pem",
    "tests/support/tls/wrong-host.pem",
    "tests/support/tls/untrusted.pem",
    "docs/model-composition.md",
    "docs/secret-ref-1a.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
}
UNIT = "tests/unit/reference/test_credential_https.py"
PLANE = "tests/integration/composition/test_credential_https_exchange.py"
ARCH = "tests/architecture/test_credential_https.py"


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
    phase = (
        "1 scope guard (private transport only; no public host, adapter or consumer)"
    )
    cache = ROOT / ".pytest_cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="credential-t2-", dir=cache) as tmp:
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
                "verified TLS only; no key logging; exact https targets",
                UNIT,
                "test_tls_context_is_verified_and_never_key_logs",
                "test_unverified_contexts_are_refused",
                "test_targets_are_exact_https_only",
                "test_target_shape",
                "test_bad_certificates_fail_before_any_request",
                "test_connection_refused_is_a_connect_failure",
                "test_no_credential_before_the_handshake",
            )
            focused(
                3,
                "minimal request shape; bounded response framing; no redirect",
                UNIT,
                "test_exact_minimal_request_shape",
                "test_complete_non_success_responses_are_returned_not_followed",
                "test_incomplete_or_unsupported_responses_are_not_complete",
                "test_response_timeout_is_bounded_and_incomplete",
                "test_oversized_request_body_refused",
                "test_resources_are_released_on_every_path",
                "test_flight_repr_and_errors_never_carry_the_token",
            )
            focused(
                4,
                "INTENDED -> claim -> S1 handoff -> observation -> settlement",
                PLANE,
                "test_complete_success_is_completed_and_attributed",
                "test_complete_rejection_is_provider_rejected",
                "test_sent_without_complete_response_is_unknown",
                "test_response_timeout_stays_unknown",
                "test_tls_failure_is_not_sent_without_realizing_the_secret",
            )
            focused(
                5,
                "final-gate currentness and SRCP-1 margin before H",
                PLANE,
                "test_refused_at_the_final_gate_sends_nothing",
            )
            focused(
                6,
                "gated partial writes; invalidation between writes stays UNKNOWN",
                PLANE,
                "test_partial_and_would_block_writes_complete_under_the_gate",
                "test_invalidation_between_partial_writes_stops_and_stays_unknown",
            )
            focused(
                7,
                "wall-clock violation after H detected, not prevented",
                PLANE,
                "test_wall_clock_violation_after_h_is_detected_not_prevented",
            )
            focused(
                8,
                "receipt/claim adversarial and recipient binding",
                PLANE,
                "test_forged_or_reused_receipts_never_realize_or_send",
                "test_receipt_is_single_use",
                "test_recovered_attempt_cannot_be_claimed",
                "test_recipient_mismatch_refused_before_connecting",
            )
            focused(
                9,
                "canaries and ambient inputs (proxy, CA bundle, key log, API keys)",
                PLANE,
                "test_no_canary_anywhere",
                "test_ambient_proxy_ca_and_keylog_inputs_are_ignored",
            )
            tests("10 all T2 tests and boundaries", UNIT, PLANE, ARCH)
            tests(
                "11 ownership and import boundaries",
                "tests/architecture/test_import_boundaries.py",
                "tests/architecture/test_remote_disclosure.py",
                "tests/architecture/test_remote_attempts.py",
                "tests/architecture/test_secret_source_s1.py",
                "tests/architecture/test_secret_ref.py",
                "tests/architecture/test_local_host.py",
                "tests/architecture/test_openai_compatible.py",
            )
            tests(
                "12 attempt custody, S1, disclosure and Secret regressions",
                "tests/unit/reference/test_remote_attempts.py",
                "tests/integration/composition/test_remote_attempt_custody.py",
                "tests/unit/reference/test_secret_source_s1.py",
                "tests/unit/reference/test_secret_ref.py",
                "tests/integration/composition/test_remote_disclosure_gate.py",
                "tests/integration/composition/test_remote_disclosure.py",
                "tests/unit/governance/test_disclosure.py",
            )
            tests(
                "13 durable custody, OpenAI-compatible LOCAL and Ollama regressions",
                "tests/unit/reference/test_secret_durable_custody.py",
                "tests/unit/reference/test_openai_compatible.py",
                "tests/integration/composition/test_openai_compatible.py",
                "tests/unit/reference/test_model.py",
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
                    PLANE,
                    ARCH,
                    "tests/support/tls_server.py",
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
        "CREDENTIAL-HTTPS-T2 LOCAL VALIDATION PASSED - offline; synthetic local "
        "TLS only; no external network, provider, retry or REMOTE enablement"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
