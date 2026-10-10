"""REMOTE-CHAT-HTTP-STATUS-DIAGNOSTICS-1 operator-run offline qualification.

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
CHANGED_FILES = (
    "scripts/hf_inference_compatibility_probe.py",
    "scripts/tests/test_hf_inference_compatibility_probe.py",
    "src/legoai/runtime/_composition/remote_model.py",
    "src/legoai/runtime/local.py",
    "tests/integration/composition/test_openai_compatible_remote.py",
    "tests/architecture/test_local_host.py",
    "validate_remote_chat_http_status_diagnostics_1.py",
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
            "offline plan; no live execution",
            [sys.executable, CHANGED_FILES[0], "--plan"],
        )
        run(
            "REMOTE complete-status, HF, Agent, disclosure and Secret regressions",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                CHANGED_FILES[1],
                "scripts/tests/test_hf_nscale_policy.py",
                "scripts/tests/test_hf_discovery_eligibility.py",
                "scripts/tests/test_hf_allowlist_overlap.py",
                "tests/integration/composition/test_agent.py",
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
        "REMOTE-CHAT-HTTP-STATUS-DIAGNOSTICS-1 OFFLINE CHECKS PASSED; "
        "LIVE PROBE REQUIRES SEPARATE AUTHORIZATION; "
        "no HF API calls, no named-provider qualification"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
