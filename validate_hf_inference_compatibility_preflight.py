"""Operator-run offline validation; no live HF probe and no qualification claim.

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
NEW_FILES = (
    "scripts/hf_inference_compatibility_probe.py",
    "scripts/tests/test_hf_inference_compatibility_probe.py",
    "validate_hf_inference_compatibility_preflight.py",
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
        run("offline blocked plan", [sys.executable, NEW_FILES[0], "--plan"])
        run(
            "HF preflight and existing discovery/REMOTE/security contracts",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                NEW_FILES[1],
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
        run("typing", [sys.executable, "-m", "mypy", *NEW_FILES])
        run("lint", [sys.executable, "-m", "ruff", "check", *NEW_FILES])
        run("format", [sys.executable, "-m", "ruff", "format", "--check", *NEW_FILES])
        run("diff whitespace", ["git", "diff", "--check"])
    except (OSError, subprocess.CalledProcessError):
        print(f"FAIL: {phase}; later phases NOT RUN")
        return 1
    print(
        "HF PREFLIGHT OFFLINE CHECKS PASSED; LIVE PREFLIGHT STILL BLOCKED; "
        "no HF API calls, no named-provider qualification"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
