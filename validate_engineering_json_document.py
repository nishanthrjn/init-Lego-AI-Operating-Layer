"""ENG-JSON-1 validation: ADR-021 JSON document representation.

Run from the repository root (Windows, Docker Desktop Linux engine, context
desktop-linux, with the CR-2a PYTHON_CHECKS image already built locally):

    uv run python .\\validate_engineering_json_document.py

It proves the slice's scope (only the ADR-021 decoder and its three call sites
change in runtime code; Core, ForgeAI runtime, definitions and public values
are untouched), the decoder contract, every Agent through its public API, the
M8.1-M8.3 and full Engineering regressions, and the LQ1 harness mirror
(schema 3) with ForgeAI-3 regressions. No live model is contacted. Every
pytest phase uses a fresh --basetemp. Streams output, stops at the first
failed phase and exits non-zero on failure.

The ForgeAI-3 and LQ1 validators assert that their own slices changed no
`packages` source relative to HEAD; run them after ENG-JSON-1 is committed.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINEERING = ROOT / "packages" / "legoai-engineering"
FORGEAI = ROOT / "examples" / "forgeai"
SELF = ROOT / "validate_engineering_json_document.py"
IMAGE = "sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df"
PACKAGE = "packages/legoai-engineering/"
SOURCE = PACKAGE + "src/legoai_engineering/"
CALL_SITES = [SOURCE + f"{agent}/api.py" for agent in ("analyst", "coding", "reviewer")]
DECODER = SOURCE + "_json_document.py"
ALLOWED_PACKAGE_CHANGES = {
    *CALL_SITES,
    DECODER,
    PACKAGE + "tests/test_json_document.py",
    PACKAGE + "tests/test_architecture.py",
    PACKAGE + "tests/test_package_install.py",
    PACKAGE + "README.md",
}
CALL_SITE_LINES = {
    ("+", "from legoai_engineering._json_document import json_document"),
    ("-", "value: object = json.loads(output, object_pairs_hook=_unique_object)"),
    (
        "+",
        "value: object = json.loads(json_document(output), "
        "object_pairs_hook=_unique_object)",
    ),
}
DOCUMENT = "tests/test_json_document.py"


def select(module: str, *names: str) -> list[str]:
    return [f"{module}::{name}" for name in names]


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
    with tempfile.TemporaryDirectory(prefix="eng-json-1-") as temporary:
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
            phase = "1 environment"
            for tool, value in (("uv", uv), ("git", git), ("docker", docker)):
                if value is None:
                    raise RuntimeError(f"{tool} is required on PATH")
            if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
                raise RuntimeError(
                    "run through the locked root environment: "
                    "uv run python .\\validate_engineering_json_document.py"
                )
            assert uv is not None and git is not None and docker is not None
            run(
                "1 no Core or ForgeAI runtime change (tracked)",
                [
                    git,
                    "diff",
                    "--exit-code",
                    "--stat",
                    "HEAD",
                    "--",
                    "src/legoai",
                    "examples/forgeai/src",
                ],
            )
            untracked = git_text(
                "status",
                "--porcelain",
                "--untracked-files=all",
                "--",
                "src/legoai",
                "examples/forgeai/src",
            ).strip()
            check(
                "1b no Core or ForgeAI runtime change (untracked)",
                f"untracked runtime files:\n{untracked}" if untracked else None,
            )
            changed = {
                line[3:].strip().strip('"')
                for line in git_text(
                    "status", "--porcelain", "--untracked-files=all", "--", "packages"
                ).splitlines()
            }
            unexpected = sorted(changed - ALLOWED_PACKAGE_CHANGES)
            check(
                "1c package changes limited to the ADR-021 slice",
                f"unexpected package changes: {unexpected}" if unexpected else None,
            )
            problems = []
            for path in CALL_SITES:
                lines = {
                    (line[0], line[1:].strip())
                    for line in git_text("diff", "-U0", "HEAD", "--", path).splitlines()
                    if line[:1] in {"+", "-"} and line[:3] not in {"+++", "---"}
                }
                if lines != CALL_SITE_LINES:
                    problems.append(f"{path}: {sorted(lines)}")
            check(
                "1d each Agent changes only the decoder import and its json.loads "
                "call (public API, definitions and validators unchanged)",
                "\n".join(problems) or None,
            )
            run(
                "1e qualified image presence",
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
                "1f Engineering environment (locked sync)",
                [uv, "sync", "--locked", "--extra", "analyst"],
                cwd=ENGINEERING,
                env=project_environment,
            )
            tests(
                "2 decoder: raw unchanged, exact fences decoded",
                ENGINEERING,
                *select(
                    DOCUMENT,
                    "test_non_fenced_replies_are_returned_unchanged",
                    "test_exact_fences_yield_the_document",
                ),
            )
            tests(
                "3 decoder: every other envelope rejected; one document only",
                ENGINEERING,
                *select(
                    DOCUMENT,
                    "test_other_envelopes_are_returned_unchanged_and_stay_invalid",
                    "test_decoded_text_that_is_not_one_document_is_rejected",
                    "test_decoder_is_pure_standard_text_handling",
                ),
            )
            tests(
                "4 Coding Agent: fenced == raw; rejections keep status; size on "
                "whole reply; no retry",
                ENGINEERING,
                *select(
                    DOCUMENT,
                    "test_coding_fenced_reply_equals_the_raw_reply",
                    "test_coding_rejections_keep_the_existing_status",
                    "test_output_size_is_validated_on_the_whole_fenced_reply",
                ),
            )
            tests(
                "5 Independent Reviewer: fenced == raw; rejections keep status",
                ENGINEERING,
                *select(
                    DOCUMENT,
                    "test_review_fenced_reply_equals_the_raw_reply",
                    "test_review_rejections_keep_the_existing_status",
                ),
            )
            tests(
                "6 Repository Analyst: fenced == raw; rejections keep status",
                ENGINEERING,
                *select(
                    DOCUMENT,
                    "test_analysis_fenced_reply_equals_the_raw_reply",
                    "test_analysis_rejections_keep_the_existing_status",
                ),
            )
            tests(
                "7 M8.1 / M8.2 / M8.3 regression suites",
                ENGINEERING,
                "tests/test_analyst.py",
                "tests/test_analyst_architecture.py",
                "tests/test_reviewer.py",
                "tests/test_coding.py",
                "tests/test_coding_m4.py",
            )
            tests(
                "8 Engineering architecture and wheel contents",
                ENGINEERING,
                "tests/test_architecture.py",
                "tests/test_package_install.py",
            )
            tests("9 full Engineering suite (incl. real Docker)", ENGINEERING)
            project(
                "10 Engineering mypy",
                ENGINEERING,
                "python",
                "-m",
                "mypy",
                "--cache-dir",
                str(base / "mypy-e"),
                "src",
                "tests",
                "examples",
            )
            project(
                "11 Engineering Ruff lint",
                ENGINEERING,
                "python",
                "-m",
                "ruff",
                "check",
                "--no-cache",
                "src",
                "tests",
                "examples",
            )
            project(
                "12 Engineering Ruff format",
                ENGINEERING,
                "python",
                "-m",
                "ruff",
                "format",
                "--check",
                "--no-cache",
                "src",
                "tests",
                "examples",
            )
            run(
                "13 ForgeAI environment (locked sync)",
                [uv, "sync", "--locked"],
                cwd=FORGEAI,
                env=project_environment,
            )
            tests(
                "14 LQ1 mirror of ADR-021 (classifier agrees with the runtime)",
                FORGEAI,
                "evaluation/tests/test_lq1_outputs.py",
            )
            tests(
                "15 LQ1 schema 3, fold, privacy and observer non-interference",
                FORGEAI,
                "evaluation/tests/test_lq1_diagnostics.py",
                "evaluation/tests/test_lq1_checkdiag.py",
                "evaluation/tests/test_lq1_observer.py",
            )
            tests(
                "16 full LQ1 harness suite (incl. real Docker)",
                FORGEAI,
                "evaluation/tests",
            )
            tests(
                "17 ForgeAI-3 regression subset",
                FORGEAI,
                "tests/test_architecture.py",
                "tests/test_domain.py",
                "tests/test_worker.py",
                "tests/test_review.py",
                "tests/test_rework.py",
                "tests/test_cli.py",
            )
            project(
                "18 ForgeAI mypy",
                FORGEAI,
                "python",
                "-m",
                "mypy",
                "--cache-dir",
                str(base / "mypy-f"),
                "src",
                "tests",
                "demo.py",
                "evaluation/forgeai_eval",
                "evaluation/tests",
                "evaluation/run.py",
            )
            project(
                "19 ForgeAI Ruff lint",
                FORGEAI,
                "python",
                "-m",
                "ruff",
                "check",
                "--no-cache",
                "src",
                "tests",
                "demo.py",
                "evaluation",
            )
            run(
                "19b ForgeAI Ruff format",
                [
                    uv,
                    "run",
                    "--locked",
                    "--no-sync",
                    "python",
                    "-m",
                    "ruff",
                    "format",
                    "--check",
                    "--no-cache",
                    "src",
                    "tests",
                    "demo.py",
                    "evaluation",
                ],
                cwd=FORGEAI,
                env=project_environment,
            )
            run(
                "20 validator mypy",
                [python, "-m", "mypy", "--cache-dir", str(base / "mypy-v"), str(SELF)],
            )
            run("20b validator Ruff lint", [python, "-m", "ruff", "check", str(SELF)])
            run(
                "20c validator Ruff format",
                [python, "-m", "ruff", "format", "--check", str(SELF)],
            )
            adr = (ROOT / "adrs" / "ADR-021.md").read_text(encoding="utf-8")
            check(
                "21 ADR-021 accepted",
                None if "Status: Accepted" in adr else "ADR-021 is not Accepted",
            )
            run("22 git diff --check", [git, "diff", "--check"])
        except Exception as error:
            for item in completed:
                print("PASS " + item)
            print(f"FAIL {phase}; later phases NOT RUN")
            if not isinstance(error, subprocess.CalledProcessError):
                print(f"reason: {error}")
                return 1
            return error.returncode if error.returncode > 0 else 1
    for item in completed:
        print("PASS " + item)
    print(
        "ENG-JSON-1 VALIDATION PASSED - ADR-021 JSON document representation; "
        "no live model was contacted. Run validate_forgeai_3.py and "
        "validate_forgeai_lq1.py after committing (they require no package "
        "change relative to HEAD)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
