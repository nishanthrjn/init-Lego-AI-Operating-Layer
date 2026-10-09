r"""Offline qualification: uv run python .\validate_kisski_compatibility_preflight.py.

KISSKI-COMPATIBILITY-1 harness/live-preflight only: proves the operator-run
probe (scripts/kisski_compatibility_probe.py) composes only the qualified
governed paths, can make at most one governed POST /models and one governed
SYNTHETIC chat, takes the credential only through S1 hidden input (twice,
one revision per purpose), and that --plan touches nothing. Synthetic local
TLS and S1 material only; this validation never contacts the real provider.
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from validate_secret_use_durable_custody_1 import IMPLEMENTATION_TEST_DIRECTORIES

ROOT = Path(__file__).resolve().parent
BASE = "ad5c987"  # KISSKI-COMPATIBILITY-1 harness committed (last before
# KISSKI-PROBE-DIAGNOSTICS-1)
HARNESS = "scripts/kisski_compatibility_probe.py"
TESTS = "scripts/tests/test_kisski_compatibility_probe.py"
SELF = "validate_kisski_compatibility_preflight.py"
DISCOVERY = "tests/integration/composition/test_provider_discovery.py"
PYTHON_FILES = (HARNESS, TESTS, DISCOVERY, SELF)
ALLOWED = set(PYTHON_FILES) | {
    "docs/model-composition.md",
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
    phase = "1 scope guard (harness, docs and tests only; no Core change)"
    cache = ROOT / ".pytest_cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="kisski-preflight-", dir=cache) as tmp:
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
                "exact provider facts, declaration and admissions",
                TESTS,
                "test_live_provider_facts_are_exact",
                "test_declaration_states_only_documented_facts",
                "test_chat_admission_is_synthetic_only_and_exact",
                "test_discovery_admission_is_exact",
            )
            focused(
                3,
                "two hidden provisionings, one revision per purpose, no crossing",
                TESTS,
                "test_two_separate_revisions_with_distinct_purposes",
                "test_revisions_never_cross_purposes",
                "test_ambient_keys_are_never_used",
            )
            focused(
                4,
                "synthetic end to end: one /models, operator selection, one chat",
                TESTS,
                "test_synthetic_end_to_end_discovery_then_one_chat",
                "test_operator_choice_is_honored_never_automatic",
                "test_invalid_selection_makes_no_chat_call",
                "test_non_ready_reply_is_still_protocol_pass",
            )
            focused(
                5,
                "failure classification; discovery failure prevents chat; no retry",
                TESTS,
                "test_discovery_failure_prevents_chat",
                "test_tls_failure_prevents_chat_and_sends_nothing",
                "test_chat_contract_failure_is_reported_once",
            )
            focused(
                6,
                "plan mode and live-entry guards; no ambient or file credential",
                TESTS,
                "test_plan_mode_has_no_network_prompt_or_credential",
                "test_live_header_precedes_credential_prompts_and_never_claims_no_network",
                "test_live_entry_requires_an_interactive_terminal",
                "test_only_option_is_plan",
                "test_script_reads_no_ambient_or_file_credential_and_no_forgeai",
            )
            tests("7 all harness tests", TESTS)
            tests(
                "8 provider discovery and REMOTE chat/embedding regressions",
                "tests/integration/composition/test_provider_discovery.py",
                "tests/unit/governance/test_provider_control.py",
                "tests/unit/reference/test_model_list.py",
                "tests/integration/composition/test_openai_compatible_remote.py",
                "tests/integration/composition/test_secret_uses.py",
                "tests/unit/reference/test_openai_compatible_exchange.py",
            )
            tests(
                "9 T2, attempt custody, S1, disclosure and Secret regressions",
                "tests/unit/reference/test_credential_https.py",
                "tests/integration/composition/test_credential_https_exchange.py",
                "tests/unit/reference/test_remote_attempts.py",
                "tests/integration/composition/test_remote_attempt_custody.py",
                "tests/unit/reference/test_secret_source_s1.py",
                "tests/unit/reference/test_secret_ref.py",
                "tests/integration/composition/test_remote_disclosure_gate.py",
                "tests/unit/governance/test_disclosure.py",
            )
            tests(
                "10 architecture and import boundaries",
                "tests/architecture",
                "--deselect",
                STALE,
            )
            run(
                "11 mypy",
                [
                    "mypy",
                    "--cache-dir",
                    str(temp / "mypy"),
                    "src",
                    HARNESS,
                    TESTS,
                    str(Path(__file__).resolve()),
                ],
            )
            run("12 Ruff lint", ["ruff", "check", "--no-cache", *PYTHON_FILES])
            run(
                "13 Ruff format",
                ["ruff", "format", "--check", "--no-cache", *PYTHON_FILES],
            )
            phase = "14 git diff check"
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
        "KISSKI-COMPATIBILITY-1 HARNESS LOCAL VALIDATION PASSED - offline; synthetic "
        "local TLS and S1 material only; this validation contacted no provider; a "
        "live run still "
        "requires explicit authorization"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
