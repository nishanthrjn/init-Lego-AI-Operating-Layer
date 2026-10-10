"""ForgeAI REMOTE qualification: local TLS only; one labelled PyPI preparation.

No Internet model endpoint. The historical remote validator's original slice
allowlist is not applicable to this later application change; its applicable
regression suites run here directly, without altering that validator.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGEAI = ROOT / "examples/forgeai"
ENGINEERING = ROOT / "packages/legoai-engineering"
REMOTE_TESTS = (
    "tests/integration/composition/test_openai_compatible_remote.py",
    "tests/integration/composition/test_secret_uses.py",
    "tests/unit/reference/test_openai_compatible_exchange.py",
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
LOCAL_TESTS = (
    "tests/unit/reference/test_openai_compatible.py",
    "tests/integration/composition/test_openai_compatible.py",
    "tests/unit/reference/test_model.py",
    "tests/integration/composition/test_local_host.py",
    "tests/integration/composition/test_model_governed.py",
    "tests/integration/composition/test_agent.py",
)


def main() -> int:
    uv = shutil.which("uv")
    if uv is None:
        print("FAIL: uv required")
        return 1
    phase = "prerequisites"

    def run(
        name: str, args: list[str], cwd: Path = ROOT, *, docker: bool = False
    ) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + name, flush=True)
        env = os.environ.copy()
        env.pop("VIRTUAL_ENV", None)
        env.pop("LEGOAI_QUALIFY_PROJECT_CHECKS", None)
        env.pop("LEGOAI_QUALIFY_FORGEAI_REMOTE", None)
        env["UV_OFFLINE"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        if docker:
            env["LEGOAI_QUALIFY_FORGEAI_REMOTE"] = "1"
        subprocess.run(args, cwd=cwd, env=env, check=True, shell=False)

    def project(name: str, cwd: Path, *args: str, docker: bool = False) -> None:
        assert uv is not None
        run(
            name,
            [uv, "run", "--locked", "--no-sync", "python", *args],
            cwd,
            docker=docker,
        )

    try:
        run(
            "locked offline ForgeAI sync",
            [uv, "sync", "--locked", "--offline"],
            FORGEAI,
        )
        run(
            "locked offline Engineering sync",
            [uv, "sync", "--locked", "--offline", "--extra", "analyst"],
            ENGINEERING,
        )
        project(
            "ForgeAI remote TLS/security, CLI and PROJECT regressions",
            FORGEAI,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_remote_profile.py",
            "tests/test_project_check_profile.py",
            "tests/test_architecture.py",
            "-k",
            "not real_docker_remote_profile_independence",
        )
        run(
            "qualified REMOTE, Secret/S1, disclosure, custody and T2 regressions (local TLS)",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                *REMOTE_TESTS,
            ],
        )
        run(
            "LOCAL model and Agent regressions",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                *LOCAL_TESTS,
            ],
        )
        run(
            "Core architecture boundaries",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/architecture/test_openai_compatible_remote.py",
                "tests/architecture/test_remote_disclosure.py",
                "tests/architecture/test_remote_attempts.py",
                "tests/architecture/test_credential_https.py",
                "tests/architecture/test_import_boundaries.py",
            ],
        )
        project(
            "Engineering preparation and sandbox regressions",
            ENGINEERING,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_check_preparation.py",
            "tests/test_checks.py",
            "tests/test_checks_sandboxed.py",
            "tests/test_sandbox.py",
            "tests/test_sandbox_readiness.py",
            "tests/test_architecture.py",
        )
        project("typing ForgeAI", FORGEAI, "-m", "mypy", "src", "tests", "demo.py")
        project(
            "lint ForgeAI", FORGEAI, "-m", "ruff", "check", "src", "tests", "demo.py"
        )
        project(
            "format ForgeAI",
            FORGEAI,
            "-m",
            "ruff",
            "format",
            "--check",
            "src",
            "tests",
            "demo.py",
        )
        for tool in ("mypy", "ruff"):
            args = [sys.executable, "-m", tool]
            if tool == "ruff":
                args.append("check")
            run("validator " + tool, [*args, str(Path(__file__).resolve())])
        run(
            "validator format",
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                str(Path(__file__).resolve()),
            ],
        )
        project(
            "real Docker + local TLS: GENERIC and PROJECT (ONE PyPI wheel acquisition; checks offline)",
            FORGEAI,
            "-m",
            "pytest",
            "-q",
            "-s",
            "-p",
            "no:cacheprovider",
            "tests/test_remote_profile.py::test_real_docker_remote_profile_independence",
            docker=True,
        )
        run(
            "full historical v0.1 regression validator on current checkout",
            [sys.executable, str(ROOT / "validate_forgeai_v01.py")],
        )
        run("diff whitespace", ["git", "diff", "--check"])
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"FAIL {phase}: {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI REMOTE MODEL PROFILE LOCAL VALIDATION PASSED: synthetic local TLS only; no external model provider; explicit PyPI preparation, offline checks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
