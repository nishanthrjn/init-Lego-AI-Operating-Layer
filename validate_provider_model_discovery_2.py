"""PROVIDER-MODEL-DISCOVERY-2 operator-run offline qualification.

Uses existing locked environments. Missing dependencies fail; this script does
not install anything. Local synthetic TLS regression servers are permitted.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from validate_forgeai_remote_model_profile_1 import REMOTE_TESTS

ROOT = Path(__file__).resolve().parent
FORGEAI = ROOT / "examples/forgeai"
CHANGED_FILES = (
    "scripts/hf_inference_compatibility_probe.py",
    "scripts/tests/test_hf_inference_compatibility_probe.py",
    "validate_provider_model_discovery_2.py",
    "src/legoai/governance/provider_control.py",
    "src/legoai/reference/_credential_https.py",
    "src/legoai/reference/_remote_attempts.py",
    "src/legoai/reference/model_openai_compatible.py",
    "src/legoai/runtime/_composition/credential_https.py",
    "src/legoai/runtime/_composition/provider_discovery.py",
    "tests/support/provider_discovery.py",
    "tests/support/tls_server.py",
    "tests/integration/composition/test_provider_discovery.py",
    "tests/integration/composition/test_provider_discovery_v2.py",
    "tests/architecture/test_credential_https.py",
    "tests/architecture/test_local_host.py",
    "tests/architecture/test_package_install.py",
)


def main() -> int:
    uv = shutil.which("uv")
    if uv is None:
        print("FAIL: uv required; no checks run")
        return 1
    env = os.environ.copy()
    for key in (
        "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
        "VIRTUAL_ENV",
        "LEGOAI_QUALIFY_PROJECT_CHECKS",
        "LEGOAI_QUALIFY_FORGEAI_REMOTE",
    ):
        env.pop(key, None)
    env["UV_OFFLINE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    phase = "prerequisites"

    def run(name: str, args: list[str], cwd: Path = ROOT) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + name, flush=True)
        subprocess.run(args, cwd=cwd, env=env, check=True, shell=False)

    try:
        run(
            "offline plan; live readiness gate disabled",
            [sys.executable, CHANGED_FILES[0], "--plan"],
        )
        run(
            "discovery v2, HF synthetic flow, KISSKI POST and REMOTE/security regressions",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                CHANGED_FILES[1],
                "scripts/tests/test_kisski_compatibility_probe.py",
                "tests/integration/composition/test_provider_discovery_v2.py",
                "tests/unit/governance/test_provider_control.py",
                "tests/unit/reference/test_model_list.py",
                "tests/integration/composition/test_provider_discovery.py",
                *REMOTE_TESTS,
            ],
        )
        run(
            "architecture",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/architecture",
            ],
        )
        run(
            "ForgeAI remote profile (synthetic TLS, no Docker acquisition)",
            [
                uv,
                "run",
                "--locked",
                "--offline",
                "--no-sync",
                "python",
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_remote_profile.py",
                "tests/test_architecture.py",
                "-k",
                "not real_docker_remote_profile_independence",
            ],
            FORGEAI,
        )
        run("typing", [sys.executable, "-m", "mypy", *CHANGED_FILES])
        run("lint", [sys.executable, "-m", "ruff", "check", *CHANGED_FILES])
        run(
            "format",
            [sys.executable, "-m", "ruff", "format", "--check", *CHANGED_FILES],
        )
        run("diff whitespace", ["git", "diff", "--check"])
    except OSError, subprocess.CalledProcessError:
        print(f"FAIL: {phase}; later phases NOT RUN")
        return 1
    print(
        "PROVIDER-MODEL-DISCOVERY-2 OFFLINE CHECKS PASSED; LIVE GATE STILL DISABLED; "
        "no HF API calls, no named-provider qualification"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
