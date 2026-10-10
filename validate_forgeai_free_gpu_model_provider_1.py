"""Offline interoperability checks; --full additionally runs legacy Docker suites."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGEAI = ROOT / "examples/forgeai"
CORE = (
    "src/legoai/intelligence/model/ports.py",
    "src/legoai/intelligence/model/values.py",
    "src/legoai/reference/model_openai_compatible.py",
    "src/legoai/reference/_credential_https.py",
    "src/legoai/runtime/api.py",
    "src/legoai/runtime/local.py",
    "src/legoai/runtime/_composition/agent.py",
    "src/legoai/runtime/_composition/model_governed.py",
    "src/legoai/runtime/_composition/credential_https.py",
    "src/legoai/runtime/_composition/remote_model.py",
    "tests/unit/reference/test_model_provider_diagnostics.py",
    "tests/architecture/test_local_host.py",
    "tests/architecture/test_remote_disclosure.py",
    "tests/architecture/test_package_install.py",
    "tests/integration/composition/test_openai_compatible.py",
    "validate_forgeai_free_gpu_model_provider_1.py",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    phase = "start"

    def run(name: str, directory: Path, command: list[str]) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + name, flush=True)
        subprocess.run(command, cwd=directory, check=True, timeout=1800)

    forge = ["uv", "run", "--locked", "--offline", "--no-sync", "python"]
    try:
        run(
            "provider contracts + ForgeAI architecture",
            FORGEAI,
            [
                *forge,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_provider.py",
                "tests/test_architecture.py",
            ],
        )
        run(
            "full Core regression including architecture",
            ROOT,
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
        )
        run(
            "ForgeAI remote regressions (synthetic TLS)",
            FORGEAI,
            [
                *forge,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_remote_profile.py",
                "-k",
                "not real_docker",
            ],
        )
        if args.full:
            run(
                "full ForgeAI regression (requires existing Docker runtime)",
                FORGEAI,
                [*forge, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
            )
        for tool, options in (
            ("mypy", []),
            ("ruff", ["check"]),
            ("ruff", ["format", "--check"]),
        ):
            run(
                "Core " + tool + " ".join(options),
                ROOT,
                [
                    sys.executable,
                    "-m",
                    tool,
                    *options,
                    *(
                        p
                        for p in CORE
                        if tool != "mypy"
                        or p
                        != "tests/integration/composition/test_openai_compatible.py"
                    ),
                ],
            )
            run(
                "ForgeAI " + tool + " ".join(options),
                FORGEAI,
                [*forge, "-m", tool, *options, "src", "tests", "demo.py"],
            )
        run("diff whitespace", ROOT, ["git", "diff", "--check"])
    except OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired:
        print("FAIL: " + phase + "; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-FREE-GPU-MODEL-PROVIDER-1 OFFLINE CHECKS PASSED; no live endpoint qualification"
    )
    if not args.full:
        print(
            "Legacy full ForgeAI/Docker regression not included; use --full separately"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
