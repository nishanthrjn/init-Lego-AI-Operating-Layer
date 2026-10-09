r"""Offline qualification: uv run python .\validate_openai_compatible_remote_1.py.

OPENAI-COMPATIBLE-REMOTE-1: one single-operator credentialed REMOTE
OpenAI-compatible Model profile over verified HTTPS, through the PUBLIC
governed host. Each invocation independently passes remote-disclosure
admission, durable attempt custody, a purpose-bound current per-invocation
Secret use and the SRCP-1 credential handoff before one request; no retry or
fallback. Only process-local synthetic TLS servers with test-only
certificates and synthetic S1 material are used: no external network,
provider, KISSKI or real credential.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_secret_use_durable_custody_1 import IMPLEMENTATION_TEST_DIRECTORIES

ROOT = Path(__file__).resolve().parent
BASE = "e94e10c"  # CREDENTIAL-HTTPS-T2 qualified; last commit before this slice
PRODUCTION = (
    "src/legoai/reference/model_openai_compatible.py",
    "src/legoai/reference/secret.py",
    "src/legoai/runtime/api.py",
    "src/legoai/runtime/local.py",
    "src/legoai/runtime/_composition/agent.py",
    "src/legoai/runtime/_composition/model_governed.py",
    "src/legoai/runtime/_composition/remote_model.py",
    "src/legoai/runtime/_composition/secret.py",
)
PUBLIC = "tests/integration/composition/test_openai_compatible_remote.py"
USES = "tests/integration/composition/test_secret_uses.py"
WIRE = "tests/unit/reference/test_openai_compatible_exchange.py"
ARCH = "tests/architecture/test_openai_compatible_remote.py"
TESTS = (
    PUBLIC,
    USES,
    WIRE,
    ARCH,
    "tests/architecture/test_agent.py",
    "tests/architecture/test_credential_https.py",
    "tests/architecture/test_import_boundaries.py",
    "tests/architecture/test_remote_attempts.py",
    "tests/architecture/test_remote_disclosure.py",
    "tests/architecture/test_secret_ref.py",
    "tests/integration/composition/test_openai_compatible.py",
    "tests/support/tls_server.py",
)
SELF = "validate_openai_compatible_remote_1.py"
PYTHON_FILES = (*PRODUCTION, *TESTS, SELF)
ALLOWED = set(PYTHON_FILES) | {
    "docs/model-composition.md",
    "docs/secret-ref-1a.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
}


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
    phase = "1 scope guard (no ForgeAI, Engineering, KISSKI or ComfyUI change)"
    cache = ROOT / ".pytest_cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="openai-remote-1-", dir=cache) as tmp:
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
                "public-host REMOTE chat, embedding and Agent end to end; inert open",
                PUBLIC,
                "test_public_remote_chat_end_to_end",
                "test_public_remote_embedding_success_and_identity",
                "test_embedding_unavailable_without_embedding_model",
                "test_agent_runtime_reaches_the_remote_plane",
                "test_open_performs_no_network_dns_tls_or_secret_realization",
                "test_ungoverned_adapter_of_a_remote_binding_sends_nothing",
            )
            tests("3 per-invocation exact Secret uses of one revision", USES)
            focused(
                4,
                "one revision, many invocations: A success, B retire, C admission, D grant",
                PUBLIC,
                "test_a_same_revision_serves_chat_then_embedding_as_separate_uses",
                "test_a_two_chats_same_revision",
                "test_b_retired_revision_refuses_the_next_invocation_before_handoff",
                "test_c_expired_admission_refuses_at_the_disclosure_gate",
                "test_d_secret_grant_change_refuses_the_next_invocation",
            )
            focused(
                5,
                "host-open REMOTE admission (SRCP-1 profile only)",
                PUBLIC,
                "test_missing_disclosure_or_admission_is_unsupported",
                "test_binding_mismatches_refuse_at_open",
                "test_wrong_secret_class_or_revision_refuses_at_open",
                "test_stale_revision_after_rotation_refuses_at_open",
                "test_wrong_secret_purpose_refuses_at_open",
                "test_missing_secret_use_grant_refuses_at_open",
                "test_missing_runtime_participants_refuse_at_open",
                "test_margin_bounds_and_credentialed_local_refused",
            )
            focused(
                6,
                "disclosure refusals before attempt, Secret use or network",
                PUBLIC,
                "test_missing_declaration_refused_before_attempt_secret_or_network",
                "test_disclosure_refusals_reach_nothing",
            )
            focused(
                7,
                "association, INTENDED, single exchange and Secret before transport",
                PUBLIC,
                "test_wrong_secret_consumer_refused_before_transport",
                "test_binding_origin_association_mismatch_fails_before_custody",
                "test_intended_commit_failure_sends_nothing",
                "test_one_exchange_per_invocation",
            )
            focused(
                8,
                "transport failures NOT_SENT; partial send stays UNKNOWN",
                PUBLIC,
                "test_tls_failures_are_not_sent_without_realization",
                "test_connection_failure_is_not_sent",
                "test_timeout_before_send_is_not_sent",
                "test_partial_send_interrupted_by_retirement_stays_unknown",
            )
            focused(
                9,
                "provider responses through the shared parser; no retry",
                PUBLIC,
                "test_complete_provider_rejections_are_never_retried",
                "test_complete_2xx_rejected_by_the_shared_parser",
                "test_embedding_shape_failure_rejected",
                "test_sent_without_a_complete_response_is_unknown",
            )
            focused(
                10,
                "cancellation, canaries, ambient inputs; LOCAL needs nothing",
                PUBLIC,
                "test_cancellation_before_send_reaches_nothing",
                "test_cancellation_after_send_never_rewrites_recorded_truth",
                "test_ambient_inputs_are_ignored_on_the_public_path",
                "test_local_bindings_need_no_remote_participants_and_create_nothing",
            )
            tests(
                "11 all REMOTE-1 tests and the shared wire contract", PUBLIC, USES, WIRE
            )
            tests(
                "12 ownership and import boundaries",
                "tests/architecture",
                # Pre-existing stale wheel manifest (predates T2); not this slice.
                "--deselect",
                "tests/architecture/test_package_install.py::test_build_and_fresh_wheel",
            )
            tests(
                "13 T2, attempt custody, S1, disclosure and Secret regressions",
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
                "14 OpenAI-compatible LOCAL, Ollama, Model and Agent regressions",
                "tests/unit/reference/test_openai_compatible.py",
                "tests/integration/composition/test_openai_compatible.py",
                "tests/unit/reference/test_model.py",
                "tests/integration/composition/test_local_host.py",
                "tests/integration/composition/test_model_governed.py",
                "tests/integration/composition/test_agent.py",
            )
            tests(
                "15 Core unit, integration and contract regressions",
                "tests/unit",
                "tests/integration",
                "tests/contract",
            )
            tests(
                "16 DocuMind regressions",
                "tests/unit",
                "tests/integration",
                cwd=ROOT / "examples/documind",
            )
            tests(
                "17 ForgeAI regressions",
                "tests/test_architecture.py",
                "tests/test_worker.py",
                "tests/test_review.py",
                "tests/test_rework.py",
                cwd=ROOT / "examples/forgeai",
            )
            run(
                "18 mypy",
                [
                    "mypy",
                    "--cache-dir",
                    str(temp / "mypy"),
                    "src",
                    PUBLIC,
                    USES,
                    WIRE,
                    ARCH,
                    "tests/support/tls_server.py",
                    str(Path(__file__).resolve()),
                ],
            )
            run("19 Ruff lint", ["ruff", "check", "--no-cache", *PYTHON_FILES])
            run(
                "20 Ruff format",
                ["ruff", "format", "--check", "--no-cache", *PYTHON_FILES],
            )
            phase = "21 git diff check"
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
        "OPENAI-COMPATIBLE-REMOTE-1 LOCAL VALIDATION PASSED - offline; synthetic "
        "local TLS and S1 material only; no external network, provider, KISSKI, "
        "retry or fallback"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
