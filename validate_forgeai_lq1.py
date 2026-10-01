"""ForgeAI-LQ1 validation: the evaluation HARNESS, never model quality.

Run from the repository root (Windows, Docker Desktop Linux engine, context
desktop-linux, with the CR-2a PYTHON_CHECKS image already built locally):

    uv run python .\\validate_forgeai_lq1.py

No live model is contacted: replay outputs drive ForgeAI, and the
unreachable-provider case uses a closed local port. The LQ1.1 live-run
preflight is exercised against an in-process recording HTTP stub of the
read-only Ollama endpoints, never a real Ollama. Real Docker is used for
fixture validity (hidden tests fail on templates and pass on reference
solutions). Every pytest phase uses a fresh --basetemp. Streams output, stops
at the first failed phase and exits non-zero on failure.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORGEAI = ROOT / "examples" / "forgeai"
SELF = ROOT / "validate_forgeai_lq1.py"
IMAGE = "sha256:4c64580306983d70e059f5f133f6bb3f82657c9c61fa96f562f42594f20269df"
RUNTIME = ["src/legoai", "packages", "examples/forgeai/src"]
TYPED = [
    "src",
    "tests",
    "demo.py",
    "evaluation/forgeai_eval",
    "evaluation/tests",
    "evaluation/run.py",
]
LINTED = ["src", "tests", "demo.py", "evaluation"]


def select(module: str, *names: str) -> list[str]:
    return [f"evaluation/tests/{module}.py::{name}" for name in names]


def scenarios(*numbers: int) -> list[str]:
    return [
        f"evaluation/tests/test_lq1_runner.py::test_scenario_outcomes[{number}]"
        for number in numbers
    ]


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
    with tempfile.TemporaryDirectory(prefix="forgeai-lq1-") as temporary:
        base = Path(temporary)

        def run(
            name: str,
            command: list[str],
            cwd: Path = ROOT,
            env: dict[str, str] = environment,
            expect: int = 0,
        ) -> None:
            nonlocal phase
            phase = name
            print("\n[PHASE] " + name, flush=True)
            print(subprocess.list2cmdline(command), flush=True)
            result = subprocess.run(command, cwd=cwd, env=env, check=False, shell=False)
            if result.returncode != expect:
                raise subprocess.CalledProcessError(result.returncode or 1, command)
            completed.append(name)

        def project(name: str, *arguments: str, expect: int = 0) -> None:
            assert uv is not None
            run(
                name,
                [uv, "run", "--locked", "--no-sync", *arguments],
                cwd=FORGEAI,
                env=project_environment,
                expect=expect,
            )

        def tests(name: str, *targets: str) -> None:
            project(
                name,
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
                    "uv run python .\\validate_forgeai_lq1.py"
                )
            if os.name != "nt":
                raise RuntimeError("reference scope is Windows + Docker Desktop Linux")
            assert uv is not None and git is not None and docker is not None
            run(
                "1 no runtime source change (tracked)",
                [git, "diff", "--exit-code", "--stat", "HEAD", "--", *RUNTIME],
            )
            phase = "1b no runtime source change (untracked)"
            untracked = subprocess.run(
                [git, "status", "--porcelain", "--untracked-files=all", "--", *RUNTIME],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
                shell=False,
            ).stdout.strip()
            print("\n[PHASE] " + phase, flush=True)
            if untracked:
                raise RuntimeError(f"untracked runtime files:\n{untracked}")
            completed.append(phase)
            run(
                "1c qualified image presence",
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
                "1d ForgeAI environment (locked sync)",
                [uv, "sync", "--locked"],
                cwd=FORGEAI,
                env=project_environment,
            )
            tests(
                "2 fixture manifest / schema", "evaluation/tests/test_lq1_manifest.py"
            )
            tests(
                "3 hidden-test isolation",
                *select(
                    "test_lq1_isolation",
                    "test_hidden_tests_never_enter_forgeai",
                    "test_targets_allowlist_and_check_inputs_exclude_the_hidden_root",
                ),
            )
            tests(
                "4 replay provisioning",
                *select(
                    "test_lq1_isolation",
                    "test_provisioned_repository_starts_without_hidden_material",
                ),
            )
            tests("5 replay success + hidden pass", *scenarios(1))
            tests("6 replay success + hidden fail", *scenarios(2))
            tests("7 replay rework recovery", *scenarios(3))
            tests("8 failure scenarios", *scenarios(4, 5, 6, 7))
            tests(
                "9 metric calculations",
                *select("test_lq1_runner", "test_exact_aggregate_metrics"),
            )
            tests(
                "10 reviewer / hidden matrix (MODEL-JUDGE MEASUREMENT)",
                *select("test_lq1_runner", "test_reviewer_vs_hidden_matrix"),
            )
            tests(
                "11 report completeness (fail closed)",
                *select(
                    "test_lq1_report",
                    "test_missing_metadata_fails_closed",
                    "test_revision_and_coverage_mismatch_fail_closed",
                    "test_unavailable_metrics_are_explicit",
                    "test_report_carries_no_source_prompts_or_hidden_tests",
                ),
            )
            tests(
                "12 JSON / Markdown consistency",
                *select(
                    "test_lq1_report", "test_markdown_renders_the_written_json_exactly"
                ),
            )
            tests(
                "13 unreachable-provider handling",
                "evaluation/tests/test_lq1_unreachable.py",
            )
            tests(
                "13b live preflight: success and observed-version recording",
                *select(
                    "test_lq1_preflight",
                    "test_matching_server_yields_the_observed_identity",
                    "test_live_report_records_the_observed_server_version",
                    "test_operator_cannot_supply_the_ollama_version",
                ),
            )
            tests(
                "13c live preflight: unreachable / missing model / digest "
                "mismatch fail closed (zero runs, no report)",
                *select(
                    "test_lq1_preflight",
                    "test_unreachable_server_fails_closed",
                    "test_mismatched_server_fails_closed",
                    "test_failed_preflight_runs_nothing_and_writes_no_report",
                    "test_malformed_requested_digest_is_refused_before_any_request",
                ),
            )
            tests(
                "13d replay mode needs no preflight",
                *select("test_lq1_preflight", "test_replay_mode_skips_the_preflight"),
            )
            tests(
                "14 architecture / public imports",
                "evaluation/tests/test_lq1_architecture.py",
                "tests/test_architecture.py",
            )
            tests(
                "14b real-Docker fixture validity (templates fail, references pass)",
                "evaluation/tests/test_lq1_fixtures_docker.py",
            )
            project(
                "15 mypy",
                "python",
                "-m",
                "mypy",
                "--cache-dir",
                str(base / "mypy"),
                *TYPED,
            )
            run(
                "15b mypy (validator)",
                [python, "-m", "mypy", "--cache-dir", str(base / "mypy-v"), str(SELF)],
            )
            project(
                "16 Ruff lint", "python", "-m", "ruff", "check", "--no-cache", *LINTED
            )
            run("16b Ruff lint (validator)", [python, "-m", "ruff", "check", str(SELF)])
            project(
                "17 Ruff format",
                "python",
                "-m",
                "ruff",
                "format",
                "--check",
                "--no-cache",
                *LINTED,
            )
            run(
                "17b Ruff format (validator)",
                [python, "-m", "ruff", "format", "--check", str(SELF)],
            )
            tests(
                "18 ForgeAI-3 regression subset",
                "tests/test_domain.py",
                "tests/test_worker.py",
                "tests/test_review.py",
                "tests/test_rework.py",
                "tests/test_cli.py",
            )
            project(
                "19 documented command: run.py --help",
                "python",
                "evaluation/run.py",
                "--help",
            )
            project(
                "19b live mode refuses missing metadata before any run",
                "python",
                "evaluation/run.py",
                "live",
                "--output",
                str(base / "must-not-exist"),
                expect=2,
            )
            phase = "19c no report written without metadata"
            print("\n[PHASE] " + phase, flush=True)
            if (base / "must-not-exist").exists():
                raise RuntimeError("live mode wrote output without required metadata")
            readme = (FORGEAI / "evaluation" / "README.md").read_text(encoding="utf-8")
            for text in (
                "THIS IS NOT A PRODUCTION BENCHMARK",
                "uv run python evaluation/run.py live",
                "--model-digest",
                "MODEL-JUDGE MEASUREMENT",
                "/api/version",
                "/api/tags",
            ):
                if text not in readme:
                    raise RuntimeError(f"evaluation README lacks: {text}")
            if "--ollama-version <" in readme:
                raise RuntimeError("evaluation README still documents --ollama-version")
            completed.append(phase)
            run("20 git diff --check", [git, "diff", "--check"])
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
        "FORGEAI-LQ1 HARNESS VALIDATION PASSED (including the LQ1.1 live-run "
        "preflight) - replay and a local HTTP stub only; no live model was "
        "contacted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
