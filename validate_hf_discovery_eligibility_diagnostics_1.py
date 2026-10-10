"""Operator-run offline HF eligibility qualification; no live provider or Docker."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = (
    "scripts/hf_inference_compatibility_probe.py",
    "scripts/tests/test_hf_discovery_eligibility.py",
    "validate_hf_discovery_eligibility_diagnostics_1.py",
)


def main() -> int:
    env = os.environ.copy()
    for key in (
        "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
        "LEGOAI_QUALIFY_PROJECT_CHECKS",
        "LEGOAI_QUALIFY_FORGEAI_REMOTE",
    ):
        env.pop(key, None)
    env["UV_OFFLINE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    phase = "prerequisites"

    def run(name: str, args: list[str]) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + name, flush=True)
        subprocess.run(args, cwd=ROOT, env=env, check=True, shell=False)

    try:
        run("offline plan", [sys.executable, FILES[0], "--plan"])
        run(
            "eligibility, HF synthetic flow, discovery v2 and Secret/canary regressions",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                FILES[1],
                "scripts/tests/test_hf_inference_compatibility_probe.py",
                "tests/integration/composition/test_provider_discovery_v2.py",
                "tests/unit/reference/test_secret_source_s1.py",
                "tests/integration/composition/test_secret_uses.py",
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
        run("typing", [sys.executable, "-m", "mypy", *FILES])
        run("lint", [sys.executable, "-m", "ruff", "check", *FILES])
        run("format", [sys.executable, "-m", "ruff", "format", "--check", *FILES])
        run("diff whitespace", ["git", "diff", "--check"])
    except OSError, subprocess.CalledProcessError:
        print(f"FAIL: {phase}; later phases NOT RUN")
        return 1
    print(
        "HF-DISCOVERY-ELIGIBILITY-DIAGNOSTICS-1 OFFLINE CHECKS PASSED; "
        "no provider calls; another live probe is not authorized"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
