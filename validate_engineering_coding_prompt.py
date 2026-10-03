"""ENG-CODING-PROMPT-1 operator qualification; replay/HTTP stubs, never live models.

Run: uv run python .\\validate_engineering_coding_prompt.py
Scope is pinned before this slice, so it works before and after committing.
ForgeAI regression suites run directly: legacy validator scope guards reject
an uncommitted Engineering definition. Their runtime guards are superseded here
by a stricter slice-wide allowlist, not disabled in those validators.
Requires existing locked environments, Docker Desktop and the qualified image.
"""

import ast
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINEERING = ROOT / "packages" / "legoai-engineering"
FORGEAI = ROOT / "examples" / "forgeai"
SELF = ROOT / "validate_engineering_coding_prompt.py"
BASE = "9aa272ee057e205123c562bf0ab39e59b3d6472c"
DEFINITION = "packages/legoai-engineering/src/legoai_engineering/coding/definition.py"
TEST = "tests/test_coding_prompt.py"
IMAGE = "sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df"
ALLOWED = {
    DEFINITION,
    "packages/legoai-engineering/tests/test_coding_prompt.py",
    "packages/legoai-engineering/README.md",
    "planning/ENG-CODING-PROMPT-1-DECISION.md",
    "planning/LEGOAI-CONSUMER-READINESS-PLAN.md",
    "examples/forgeai/evaluation/README.md",
    "validate_engineering_coding_prompt.py",
}


def main() -> int:
    uv = shutil.which("uv")
    git = shutil.which("git")
    docker = shutil.which("docker")
    python = sys.executable
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    project_environment = environment.copy()
    project_environment.pop("VIRTUAL_ENV", None)
    project_environment.pop("LEGOAI_SANDBOX_CHECKS_IMAGE", None)
    completed: list[str] = []
    phase = "environment"
    with tempfile.TemporaryDirectory(prefix="eng-coding-prompt-1-") as temporary:
        base = Path(temporary)

        def run(
            name: str,
            command: list[str],
            cwd: Path = ROOT,
            env: dict[str, str] = environment,
        ) -> None:
            nonlocal phase
            phase = name
            print("\n[PHASE] " + name, flush=True)
            print(subprocess.list2cmdline(command), flush=True)
            subprocess.run(command, cwd=cwd, env=env, check=True, shell=False)
            completed.append(name)

        def check(name: str, problem: str | None) -> None:
            nonlocal phase
            phase = name
            print("\n[PHASE] " + name, flush=True)
            if problem:
                raise RuntimeError(problem)
            completed.append(name)

        def git_text(*arguments: str) -> str:
            assert git is not None
            return subprocess.run(
                [git, *arguments],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
                shell=False,
            ).stdout

        def project(name: str, cwd: Path, *arguments: str) -> None:
            assert uv is not None
            run(
                name,
                [uv, "run", "--locked", "--no-sync", *arguments],
                cwd=cwd,
                env=project_environment,
            )

        def tests(name: str, cwd: Path, *targets: str) -> None:
            project(
                name,
                cwd,
                "python",
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(base / name.split()[0]),
                "-q",
                "-rs",
                *targets,
            )

        try:
            for name, tool in (("uv", uv), ("git", git), ("docker", docker)):
                if tool is None:
                    raise RuntimeError(f"{name} is required")
            assert uv is not None and git is not None and docker is not None
            changed = set(git_text("diff", "--name-only", BASE).splitlines())
            # Restrict untracked scan to code/governance areas; historical raw
            # reports and the known inaccessible test temp are outside them.
            changed.update(
                git_text(
                    "ls-files",
                    "--others",
                    "--exclude-standard",
                    "--",
                    "src",
                    "packages",
                    "adrs",
                    "planning",
                    "examples/forgeai/src",
                    "examples/forgeai/tests",
                    "examples/forgeai/evaluation",
                    "validate_engineering_coding_prompt.py",
                ).splitlines()
            )
            check(
                "1 slice scope guard",
                f"unexpected changes: {sorted(changed - ALLOWED)}"
                if changed - ALLOWED
                else None,
            )
            before = ast.parse(git_text("show", f"{BASE}:{DEFINITION}"))
            after = ast.parse((ROOT / DEFINITION).read_text(encoding="utf-8"))
            old_call = next(
                n
                for n in ast.walk(before)
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "AgentDefinition"
            )
            new_call = next(
                n
                for n in ast.walk(after)
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name)
                and n.func.id == "AgentDefinition"
            )
            new_call.args[1:3] = old_call.args[1:3]
            check(
                "1b only instructions and behavior version changed",
                None
                if ast.dump(before) == ast.dump(after)
                else "definition changed beyond version/instructions",
            )
            run(
                "1c qualified image",
                [
                    docker,
                    "--context",
                    "desktop-linux",
                    "image",
                    "inspect",
                    "--format",
                    "{{.Id}} {{.Os}}/{{.Architecture}}",
                    IMAGE,
                ],
            )
            run(
                "1d Engineering locked sync",
                [uv, "sync", "--locked", "--extra", "analyst"],
                cwd=ENGINEERING,
                env=project_environment,
            )
            run(
                "1e ForgeAI locked sync",
                [uv, "sync", "--locked"],
                cwd=FORGEAI,
                env=project_environment,
            )
            tests(
                "2 version / 3 system guidance",
                ENGINEERING,
                TEST + "::test_definition_version_and_guidance",
            )
            tests(
                "4 governed request SYSTEM / unchanged USER",
                ENGINEERING,
                TEST + "::test_governed_request_and_user_payload",
            )
            tests(
                "5 parser contract / 7 single invocation",
                ENGINEERING,
                TEST + "::test_parser_contract_and_single_call",
            )
            tests(
                "6 target authority / mutation preconditions",
                ENGINEERING,
                "tests/test_coding_m4.py",
                "tests/test_coding.py::test_request_cannot_expand_operator_scope",
                "tests/test_coding.py::test_authorization_denied_before_any_io",
            )
            tests(
                "8 model effects",
                ENGINEERING,
                "tests/test_coding.py::test_unknown_model_effect_is_preserved_without_retry",
                "tests/test_coding.py::test_cancellation_is_not_swallowed",
            )
            # Scope guard proves definition/parser/request source for Reviewer and
            # Analyst unchanged byte-for-byte modulo Git line endings.
            tests(
                "9 Reviewer definition/request regressions",
                ENGINEERING,
                "tests/test_reviewer.py",
            )
            tests(
                "10 Coding regression suite",
                ENGINEERING,
                "tests/test_coding.py",
                "tests/test_coding_m4.py",
                TEST,
            )
            tests(
                "11 Engineering relevant regressions",
                ENGINEERING,
                "tests/test_json_document.py",
                "tests/test_analyst.py",
                "tests/test_analyst_architecture.py",
                "tests/test_architecture.py",
                "tests/test_authorized_effects.py",
                "tests/test_consumer_readiness.py",
            )
            tests(
                "12 ForgeAI-1 regressions",
                FORGEAI,
                "tests/test_domain.py",
                "tests/test_worker.py",
                "tests/test_cli.py",
                "tests/test_architecture.py",
            )
            tests("13 ForgeAI-2 regressions", FORGEAI, "tests/test_review.py")
            tests(
                "14 ForgeAI-3 regressions / real Docker / installed package",
                FORGEAI,
                "tests/test_rework.py",
                "tests/test_end_to_end.py",
                "tests/test_clean_install.py",
            )
            tests(
                "15 full LQ1 harness including Docker and observer",
                FORGEAI,
                "evaluation/tests",
            )
            project(
                "16 Engineering mypy",
                ENGINEERING,
                "python",
                "-m",
                "mypy",
                "--cache-dir",
                str(base / "mypy-engineering"),
                "src",
                "tests",
                "examples",
            )
            project(
                "16b ForgeAI mypy",
                FORGEAI,
                "python",
                "-m",
                "mypy",
                "--cache-dir",
                str(base / "mypy-forgeai"),
                "src",
                "tests",
                "demo.py",
                "evaluation/forgeai_eval",
                "evaluation/tests",
                "evaluation/run.py",
            )
            run(
                "16c validator mypy",
                [
                    python,
                    "-m",
                    "mypy",
                    "--cache-dir",
                    str(base / "mypy-validator"),
                    str(SELF),
                ],
            )
            for label, directory, targets in (
                ("Engineering", ENGINEERING, ("src", "tests", "examples")),
                ("ForgeAI", FORGEAI, ("src", "tests", "demo.py", "evaluation")),
            ):
                project(
                    "17 " + label + " Ruff lint",
                    directory,
                    "python",
                    "-m",
                    "ruff",
                    "check",
                    "--no-cache",
                    *targets,
                )
                project(
                    "18 " + label + " Ruff format",
                    directory,
                    "python",
                    "-m",
                    "ruff",
                    "format",
                    "--check",
                    "--no-cache",
                    *targets,
                )
            run("17b validator lint", [python, "-m", "ruff", "check", str(SELF)])
            run(
                "18b validator format",
                [python, "-m", "ruff", "format", "--check", str(SELF)],
            )
            run("19 diff check", [git, "diff", "--check"])
        except Exception as error:
            for item in completed:
                print("PASS " + item)
            print(f"FAIL {phase}; later phases NOT RUN: {error}")
            return 1
    for item in completed:
        print("PASS " + item)
    print(
        "ENG-CODING-PROMPT-1 VALIDATION PASSED - replay/local stubs only; no live model contacted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
