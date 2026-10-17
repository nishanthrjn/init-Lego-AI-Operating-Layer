"""Maintainer-only real-sandbox qualification; replay models only."""

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

from validate_forgeai_remote_model_profile_1 import LOCAL_TESTS, REMOTE_TESTS

ROOT = Path(__file__).resolve().parent
FORGEAI = ROOT / "examples/forgeai"
ENGINEERING = ROOT / "packages/legoai-engineering"
BASE = "dca0cb999298b9ccfaea97ff318635fe2b9a4b45"
SELF = "validate_forgeai_v0_2_real_sandbox_qualification_1.py"
TARGETS = ("tests/test_v0_2_real_sandbox_qualification.py",)
ALLOWED = frozenset("examples/forgeai/" + name for name in TARGETS) | frozenset(
    {
        SELF,
        "examples/forgeai/README.md",
        "planning/FORGEAI-V0.2-REAL-SANDBOX-QUALIFICATION-1.md",
    }
)


PRESERVED = {
    "planning/FORGEAI-CONTEXT-CONFIRMATION-1.md": (
        "16ccb9d256e8142ba6da8fa499d1813c84c9eeee0173d45f0dfd24732de64683"
    ),
    "examples/forgeai/tests/test_bounded_task_qualification.py": (
        "2f895c5b60c2660db7a4319c23bd3fd15ad0c10cfdd3627e8b94ff590f90c565"
    ),
    "validate_forgeai_v0_2_bounded_task_qualification_1.py": (
        "2e5558006f4ec1e4f6d4804d532398972c26ed47b95fd0d930ddc6a499191b11"
    ),
}


def main() -> int:
    uv = shutil.which("uv")
    if uv is None:
        print("FAIL: uv required; existing locked project environments required")
        return 1
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.pop("LEGOAI_QUALIFY_PROJECT_CHECKS", None)
    env.pop("LEGOAI_QUALIFY_FORGEAI_REMOTE", None)
    env.pop("LEGOAI_SANDBOX_CHECKS_IMAGE", None)
    env.pop("LEGOAI_QUALIFY_FORGEAI_V02_SANDBOX", None)
    env["UV_OFFLINE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    phase = "qualification-only scope; all production and frozen evaluation preserved"

    def git(*args: str) -> set[str]:
        return set(
            subprocess.check_output(
                ["git", *args], cwd=ROOT, text=True, encoding="utf-8"
            ).splitlines()
        )

    def run(name: str, command: list[str], cwd: Path = ROOT) -> None:
        nonlocal phase
        phase = name
        print("\n[PHASE] " + name, flush=True)
        subprocess.run(command, cwd=cwd, env=env, check=True)

    def project(name: str, cwd: Path, *args: str) -> None:
        assert uv is not None
        run(
            name,
            [uv, "run", "--locked", "--offline", "--no-sync", "python", *args],
            cwd,
        )

    try:
        print("[PHASE] " + phase, flush=True)
        changed = (
            git("diff", "--name-only", BASE)
            | git("diff", "--cached", "--name-only", BASE)
            | git("ls-files", "--others", "--exclude-standard")
        )
        if changed - ALLOWED - PRESERVED.keys():
            raise ValueError(
                "outside bounded-task qualification scope: "
                + repr(sorted(changed - ALLOWED - PRESERVED.keys()))
            )
        for name, expected in PRESERVED.items():
            current = (ROOT / name).read_text(encoding="utf-8")
            if hashlib.sha256(current.encode()).hexdigest() != expected:
                raise ValueError("preserved prior qualification changed: " + name)
            if name in git("diff", "--cached", "--name-only", BASE):
                staged = (
                    subprocess.check_output(["git", "show", ":" + name], cwd=ROOT)
                    .decode("utf-8")
                    .replace("\r\n", "\n")
                )
                if hashlib.sha256(staged.encode()).hexdigest() != expected:
                    raise ValueError("staged prior qualification changed: " + name)
        if os.name != "nt":
            raise ValueError("requires the qualified Windows Docker Desktop Linux host")
        project(
            "Docker engine and pinned PYTHON_CHECKS image readiness; metadata only",
            FORGEAI,
            "-c",
            "import shutil,sys; from pathlib import Path; "
            "from legoai_engineering.sandbox.docker import "
            "DockerSandbox,DockerSandboxConfig,SandboxImage; "
            "from legoai_engineering.sandbox.errors import SandboxError; "
            "cli=shutil.which('docker'); "
            "sys.exit('Docker CLI missing: make the existing Docker Desktop CLI available') "
            "if cli is None else None; "
            "sandbox=DockerSandbox(DockerSandboxConfig(Path(cli),SandboxImage.PYTHON_CHECKS)); "
            "\ntry:\n sandbox.verify_ready()\nexcept SandboxError as error:\n "
            "print('Docker prerequisite failed:',error.reason.value); "
            "print('Ensure Docker Desktop Linux engine is running and the already-qualified "
            "PYTHON_CHECKS image is present. No automatic start/build/pull/install.'); "
            "sys.exit(1)",
        )
        env["LEGOAI_QUALIFY_FORGEAI_V02_SANDBOX"] = "1"
        for label, selector in (
            ("successful confirmed-context real checks", "success"),
            ("one real check-triggered rework", "check_rework"),
            ("negative controls: zero Docker workloads", "negative_pre_effect"),
        ):
            project(
                label,
                FORGEAI,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_v0_2_real_sandbox_qualification.py",
                "-k",
                selector,
            )
        env.pop("LEGOAI_QUALIFY_FORGEAI_V02_SANDBOX")
        project(
            "historical ForgeAI real-sandbox regressions",
            FORGEAI,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_end_to_end.py",
            "tests/test_v01_check_rework.py::test_pilot_regression_real_docker_ruff_b011_then_accept",
        )
        project(
            "pinned checks image confinement and real check adapters",
            ENGINEERING,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_sandbox_checks_docker.py",
            "tests/test_checks_sandboxed_docker.py",
            "-k",
            "not same_consumer_with_host_and_sandboxed_adapters",
        )
        project(
            "complete bounded lifecycle, exact confirmation and preflight controls",
            FORGEAI,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_bounded_task_qualification.py",
            "tests/test_context_confirmation.py",
            "tests/test_repository_context.py",
            "tests/test_v01_context.py",
            "-k",
            "not real_sandbox",
        )
        project(
            "ForgeAI pipeline, PROJECT, LOCAL/REMOTE and authority regressions",
            FORGEAI,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests",
            "--ignore=tests/test_end_to_end.py",
            "--ignore=tests/test_clean_install.py",
            "-k",
            "not real_docker and not real_sandbox",
        )
        project(
            "Engineering path, acquisition, coding and architecture contracts",
            ENGINEERING,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_sandbox.py",
            "tests/test_sandbox_readiness.py",
            "tests/test_checks_sandboxed.py",
            "tests/test_mutation.py",
            "tests/test_workspace.py",
            "tests/test_coding.py",
            "tests/test_coding_context.py",
            "tests/test_architecture.py",
        )
        for name, paths in (
            ("REMOTE custody and disclosure", REMOTE_TESTS),
            ("LOCAL model preservation", LOCAL_TESTS),
            (
                "KiSSKI synthetic compatibility regressions",
                (
                    "scripts/tests/test_kisski_saia_qualification.py",
                    "scripts/tests/test_kisski_saia_receive_diagnostics.py",
                    "scripts/tests/test_kisski_saia_function_call_shapes.py",
                ),
            ),
            ("architecture boundaries", ("tests/architecture",)),
        ):
            run(
                name,
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    *paths,
                ],
            )
        project("typing ForgeAI", FORGEAI, "-m", "mypy", *TARGETS)
        run("typing validator", [sys.executable, "-m", "mypy", SELF])
        project("lint ForgeAI", FORGEAI, "-m", "ruff", "check", "--no-cache", *TARGETS)
        project(
            "format ForgeAI",
            FORGEAI,
            "-m",
            "ruff",
            "format",
            "--check",
            "--no-cache",
            *TARGETS,
        )
        run(
            "lint validator",
            [sys.executable, "-m", "ruff", "check", "--no-cache", SELF],
        )
        run(
            "format validator",
            [sys.executable, "-m", "ruff", "format", "--check", "--no-cache", SELF],
        )
        run("working whitespace", ["git", "diff", "--check", BASE])
        run("staged whitespace", ["git", "diff", "--cached", "--check"])
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL: {phase}: {error}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-V0.2-REAL-SANDBOX-QUALIFICATION-1 LOCALLY QUALIFIED; "
        "CONFIRMED-CONTEXT BOUNDED TASK FLOW VERIFIED WITH REAL SANDBOXED CHECKS; "
        "REPLAY MODELS ONLY; "
        "NO LIVE MODEL QUALITY OR GLOBAL V0.2/DEPLOYMENT QUALIFICATION; "
        "NO LIVE PROVIDER EXECUTION AUTHORIZED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
