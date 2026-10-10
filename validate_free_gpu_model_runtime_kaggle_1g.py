"""Operator-run offline qualification; no installation, GPU or network execution."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPERIMENT = "experiments/kaggle/free_gpu_model_runtime"
FILES = (
    f"{EXPERIMENT}/runtime_probe.py",
    f"{EXPERIMENT}/notebook_support.py",
    f"{EXPERIMENT}/tests/test_runtime_probe.py",
    f"{EXPERIMENT}/tests/test_runtime_python.py",
    f"{EXPERIMENT}/tests/test_runtime_environment.py",
    f"{EXPERIMENT}/tests/test_cuda_environment.py",
    f"{EXPERIMENT}/tests/test_driver_observation.py",
    f"{EXPERIMENT}/tests/test_synthetic_stabilization.py",
    f"{EXPERIMENT}/tests/test_behavioral_requests.py",
)


def main() -> int:
    phase = "product boundary"

    def run(name: str, args: list[str]) -> None:
        nonlocal phase
        phase = name
        print(f"\n[PHASE] {name}", flush=True)
        subprocess.run(args, cwd=ROOT, check=True, timeout=900)

    try:
        print("[PHASE] product boundary", flush=True)
        changed = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
                "--",
                "src/legoai",
                "packages",
                "examples/forgeai/src",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if changed.strip():
            print(
                "FAIL: product changes present; isolate/review them before qualification"
            )
            return 1
        run(
            "offline experiment contracts",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                f"{EXPERIMENT}/tests",
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
        # Resolve namespace-package paths from ROOT, matching the tests' imports.
        # The deployment target is Kaggle Linux, including on Windows maintainers' PCs.
        run(
            "typing",
            [
                sys.executable,
                "-m",
                "mypy",
                "--explicit-package-bases",
                "--platform",
                "linux",
                *FILES,
                __file__,
            ],
        )
        run(
            "lint (Kaggle Python 3.10 syntax)",
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--target-version",
                "py310",
                *FILES,
                __file__,
            ],
        )
        run(
            "format",
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                "--target-version",
                "py310",
                *FILES,
                __file__,
            ],
        )
        run("diff whitespace", ["git", "diff", "--check"])
    except (OSError, subprocess.SubprocessError):
        print(f"FAIL: {phase}; later phases NOT RUN")
        return 1
    print(
        "FREE-GPU-MODEL-RUNTIME-KAGGLE-1G HARNESS LOCALLY READY; "
        "KAGGLE RUNTIME NOT QUALIFIED; no GPU or external calls"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
