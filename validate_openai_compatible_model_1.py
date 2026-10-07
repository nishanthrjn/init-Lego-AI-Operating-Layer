r"""Offline ADR-014 qualification: uv run python .\validate_openai_compatible_model_1.py.

Only process-local scripted HTTP is used. No Docker or real model provider.
Existing installed project environments are required; never sync/download.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "ed1cf96"
PRODUCTION = (
    "src/legoai/runtime/api.py",
    "src/legoai/runtime/local.py",
    "src/legoai/runtime/_composition/model_selection.py",
    "src/legoai/runtime/_composition/model_governed.py",
    "src/legoai/intelligence/model/ports.py",
    "src/legoai/reference/model.py",
    "src/legoai/reference/model_capabilities.py",
    "src/legoai/reference/model_openai_compatible.py",
)
TESTS = (
    "tests/support/openai_http.py",
    "tests/unit/reference/test_openai_compatible.py",
    "tests/integration/composition/test_openai_compatible.py",
    "tests/architecture/test_openai_compatible.py",
    "tests/architecture/test_import_boundaries.py",
    "tests/architecture/test_local_host.py",
)
PYTHON_FILES = (*PRODUCTION, *TESTS, "validate_openai_compatible_model_1.py")
ALLOWED = set(PYTHON_FILES) | {
    "planning/LEGOAI-PROVIDER-COMPUTE-PORTABILITY-DECISION.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "docs/model-composition.md",
}
UNIT = "tests/unit/reference/test_openai_compatible.py"
HOST = "tests/integration/composition/test_openai_compatible.py"
ARCH = "tests/architecture/test_openai_compatible.py"


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
    phase = "1 scope guard"
    # Workspace cache avoids Windows pytest shared-temp ownership collisions.
    cache = ROOT / ".pytest_cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="openai-model-1-", dir=cache) as temporary:
        temp = Path(temporary)

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
            focused(2, "ADR-014 accepted", ARCH, "test_accepted_adr")
            focused(
                3,
                "public API types",
                HOST,
                "test_public_settings_types_and_required_deployment",
            )
            focused(4, "closed provider union", HOST, "test_provider_union")
            focused(
                5,
                "deployment required",
                HOST,
                "test_public_settings_types_and_required_deployment",
            )
            focused(
                6,
                "REMOTE refusal",
                HOST,
                "test_remote_refused_before_admission_or_construction",
            )
            focused(
                7,
                "settings validation",
                HOST,
                "test_invalid_settings_at_open",
                "test_wrong_settings_types",
            )
            focused(
                8,
                "no credential fields",
                HOST,
                "test_public_settings_types_and_required_deployment",
            )
            focused(
                9,
                "neutral capability identity",
                HOST,
                "test_neutral_offers_and_plugin_identity",
            )
            focused(
                10, "neutral helper migration", ARCH, "test_neutral_helper_migration"
            )
            focused(
                11,
                "Ollama plugin identity",
                HOST,
                "test_neutral_offers_and_plugin_identity",
            )
            focused(
                12,
                "trusted contributions",
                HOST,
                "test_trusted_failure_contract",
                "test_portability_rows[A]",
            )
            focused(
                13,
                "private adapter boundary",
                ARCH,
                "test_private_stdlib_adapter_no_credentials",
            )
            focused(
                14, "stdlib only", ARCH, "test_private_stdlib_adapter_no_credentials"
            )
            focused(
                15,
                "inert open",
                HOST,
                "test_local_attestation_not_hostname_and_inert_open",
                "test_selected_adapter_constructed_once",
                "test_chat_only_purpose_unavailable",
            )
            focused(
                16,
                "minimal wire and versioned URL",
                UNIT,
                "test_chat_minimal_wire",
                "test_exact_versioned_url_regression",
            )
            focused(17, "max_tokens mapping", UNIT, "test_chat_minimal_wire")
            focused(
                18,
                "no Authorization header",
                UNIT,
                "test_chat_minimal_wire",
                "test_no_ambient_proxy_lookup",
            )
            focused(
                19,
                "chat success and optional usage",
                UNIT,
                "test_chat_minimal_wire",
                "test_optional_usage",
            )
            focused(
                20, "exact model identity", UNIT, "test_exact_response_identity_only"
            )
            focused(21, "stop accepted", UNIT, "test_chat_minimal_wire")
            focused(22, "length rejected", UNIT, "test_chat_rejections_no_streaming")
            focused(
                23,
                "missing and other finish reasons",
                UNIT,
                "test_chat_rejections_no_streaming",
            )
            focused(
                24,
                "malformed success and no streaming",
                UNIT,
                "test_chat_rejections_no_streaming",
                "test_malformed_json_has_no_body_exception_chain",
            )
            focused(25, "401 and 403", UNIT, "test_http_status")
            focused(26, "429 retryable rejection", UNIT, "test_http_status")
            focused(27, "503 retryable rejection", UNIT, "test_http_status")
            focused(28, "other non-2xx terminal", UNIT, "test_http_status")
            focused(
                29,
                "preflight connection",
                UNIT,
                "test_connection_refused",
                "test_dns_failure_and_ambiguous_transport",
            )
            focused(
                30,
                "timeout reset truncated uncertainty",
                UNIT,
                "test_uncertain_response",
            )
            focused(
                31,
                "embedding purposes",
                HOST,
                "test_embedding_purpose_and_governed_result",
                "test_chat_only_purpose_unavailable",
            )
            focused(
                32,
                "valid embeddings",
                UNIT,
                "test_embedding_wire_and_identity",
                "test_empty_embeddings",
            )
            focused(
                33,
                "embedding identity",
                UNIT,
                "test_embedding_invalid_identity",
                "test_exact_response_identity_only",
            )
            focused(
                34,
                "embedding count and indexes",
                UNIT,
                "test_embedding_invalid_vectors",
            )
            focused(
                35, "embedding finite vectors", UNIT, "test_embedding_invalid_vectors"
            )
            focused(
                36,
                "purpose unavailable before call",
                HOST,
                "test_chat_only_purpose_unavailable",
            )
            focused(
                37,
                "governed effects",
                HOST,
                "test_governed_effects_no_retry_or_fallback",
            )
            focused(38, "no retry", HOST, "test_governed_effects_no_retry_or_fallback")
            focused(
                39, "no fallback", HOST, "test_governed_effects_no_retry_or_fallback"
            )
            focused(40, "FixedModel conformance A", HOST, "test_portability_rows[A]")
            focused(41, "Ollama mocked conformance B", HOST, "test_portability_rows[B]")
            focused(
                42, "local fake HTTP conformance C", HOST, "test_portability_rows[C]"
            )
            tests(
                "43 application and import boundaries",
                ARCH,
                "tests/architecture/test_import_boundaries.py",
                "tests/architecture/test_local_host.py",
            )
            tests(
                "44 runtime regressions",
                "tests/integration/composition/test_local_host.py",
                "tests/integration/composition/test_model_selection.py",
            )
            tests(
                "45 model regressions",
                "tests/unit/reference/test_model.py",
                "tests/unit/reference/test_model_foundation.py",
                "tests/unit/reference/test_model_routing.py",
                "tests/unit/intelligence/test_model_values.py",
                "tests/integration/composition/test_model_governed.py",
            )
            tests(
                "46 Agent regressions",
                "tests/unit/execution/test_agent.py",
                "tests/integration/composition/test_agent.py",
                "tests/architecture/test_agent.py",
            )
            tests(
                "47 DocuMind regressions",
                "tests/unit",
                "tests/integration",
                cwd=ROOT / "examples/documind",
            )
            tests(
                "48 ForgeAI regressions",
                "tests/test_architecture.py",
                "tests/test_worker.py",
                "tests/test_review.py",
                "tests/test_rework.py",
                cwd=ROOT / "examples/forgeai",
            )
            run(
                "49 mypy",
                [
                    "mypy",
                    "--cache-dir",
                    str(temp / "mypy"),
                    "src",
                    str(Path(__file__).resolve()),
                ],
            )
            run("50 Ruff lint", ["ruff", "check", "--no-cache", *PYTHON_FILES])
            run(
                "51 Ruff format",
                ["ruff", "format", "--check", "--no-cache", *PYTHON_FILES],
            )
            phase = "52 git diff check"
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
        "OPENAI-COMPATIBLE-MODEL-1 LOCAL VALIDATION PASSED - offline; local fake HTTP only"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
