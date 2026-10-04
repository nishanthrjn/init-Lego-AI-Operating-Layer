r"""DISCOVERY-1 operator validation: no live model and no Docker required.

Run from root: uv run python .\validate_engineering_discovery_1.py
Uses locked environments, fake/replay/HTTP-stub regression tests and local files.
Unchanged Docker adapter/end-to-end tests are deliberately excluded: this slice
does not change runtime, checks, mutation, sandbox or ForgeAI dependencies.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINEERING = ROOT / "packages/legoai-engineering"
FORGEAI = ROOT / "examples/forgeai"
BASE = "fdffbb1ca7b6a37935ad2a6c421c79bde98f4a76"
ALLOWED = {
    "packages/legoai-engineering/src/legoai_engineering/repository/structure.py",
    "packages/legoai-engineering/src/legoai_engineering/repository/structure_authorized.py",
    "packages/legoai-engineering/tests/test_structure.py",
    "packages/legoai-engineering/tests/test_structure_install.py",
    "packages/legoai-engineering/tests/test_architecture.py",
    "packages/legoai-engineering/README.md",
    "packages/legoai-engineering/docs/CONSUMING.md",
    "planning/FORGEAI-TARGET-DISCOVERY-DECISION.md",
    "planning/LEGOAI-FORGEAI-MASTER-ROADMAP-2026.md",
    "adrs/ADR-018.md",
    "validate_engineering_discovery_1.py",
}


def main() -> int:
    environment = os.environ.copy()
    environment.pop("VIRTUAL_ENV", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed: list[str] = []
    phase = "prerequisites"
    with tempfile.TemporaryDirectory(prefix="discovery-1-") as temporary:
        temp = Path(temporary)

        def run(name: str, command: list[str], cwd: Path = ROOT) -> None:
            nonlocal phase
            phase = name
            print("\n[PHASE] " + name, flush=True)
            print(subprocess.list2cmdline(command), flush=True)
            subprocess.run(command, cwd=cwd, env=environment, check=True)
            completed.append(name)

        def git_text(*args: str) -> str:
            return subprocess.run(
                ["git", *args],
                cwd=ROOT,
                capture_output=True,
                encoding="utf-8",
                check=True,
            ).stdout

        def project(name: str, cwd: Path, *args: str) -> None:
            run(
                name,
                ["uv", "run", "--locked", "--no-sync", "python", "-B", "-m", *args],
                cwd,
            )

        def tests(name: str, cwd: Path, *targets: str) -> None:
            project(
                name,
                cwd,
                "pytest",
                "-q",
                "-rs",
                "-p",
                "no:cacheprovider",
                "--basetemp",
                str(temp / name.split()[0]),
                *targets,
            )

        def focused(name: str, *functions: str) -> None:
            tests(
                name, ENGINEERING, *("tests/test_structure.py::" + f for f in functions)
            )

        try:
            if not shutil.which("uv") or not shutil.which("git"):
                raise RuntimeError("uv and git must be installed")
            phase = "1 slice scope / historical ADR guard"
            print("[PHASE] " + phase, flush=True)
            changed = set(git_text("diff", "--name-only", BASE).splitlines())
            # Excludes historical raw reports and inaccessible pre-existing temp;
            # includes all production, tests and governance owners in scope.
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
                    "docs",
                    "examples/forgeai/src",
                    "examples/forgeai/tests",
                    "examples/forgeai/evaluation",
                    "validate_engineering_discovery_1.py",
                ).splitlines()
            )
            if changed - ALLOWED:
                raise RuntimeError(f"unexpected changes: {sorted(changed - ALLOWED)}")
            before = git_text("show", f"{BASE}:adrs/ADR-018.md")
            after = (ROOT / "adrs/ADR-018.md").read_text(encoding="utf-8")
            if not after.startswith(before):
                raise RuntimeError("ADR-018 historical text/status changed")
            completed.append(phase)
            run(
                "setup Engineering",
                ["uv", "sync", "--locked", "--offline", "--extra", "analyst"],
                ENGINEERING,
            )
            run("setup ForgeAI", ["uv", "sync", "--locked", "--offline"], FORGEAI)
            tests(
                "2 public API / architecture", ENGINEERING, "tests/test_architecture.py"
            )
            focused(
                "3 policy and immutable values",
                "test_policy_roots",
                "test_policy_invalid",
                "test_traversal_order_kinds_identity_privacy",
            )
            focused(
                "4 deterministic traversal",
                "test_traversal_order_kinds_identity_privacy",
            )
            focused("5 exclusions", "test_exclusions")
            focused(
                "6 bounds",
                "test_bounds",
                "test_depth_bounds",
                "test_exact_serialized_and_path_bounds",
                "test_entry_and_call_hard_ceilings",
            )
            focused(
                "7 malformed adapters",
                "test_malformed_adapter",
                "test_invalid_adapter_shape",
            )
            focused(
                "8 two-pass stability",
                "test_stability_no_retry",
                "test_traversal_order_kinds_identity_privacy",
            )
            focused(
                "9 current authorization before listing",
                "test_authority_each_listing_and_release",
            )
            focused(
                "10 mid-pass expiry / revocation", "test_live_authority_invalidation"
            )
            focused(
                "11 final release authorization",
                "test_authority_each_listing_and_release",
            )
            focused(
                "12 tenant / workspace / action",
                "test_wrong_tenant_no_io",
                "test_workspace_binding",
                "test_scope_binding",
            )
            focused("13 approvals refused", "test_approval_refused")
            focused(
                "14 privacy / safe failures",
                "test_traversal_order_kinds_identity_privacy",
                "test_unsupported_unicode",
                "test_workspace_failures",
                "test_invalid_component_configuration_safe_error",
            )
            focused(
                "15 real filesystem",
                "test_real_workspace",
                "test_real_workspace_hardlink_refusal",
            )
            tests(
                "16 M1 / M2 and complete structure suite",
                ENGINEERING,
                "tests/test_repository.py",
                "tests/test_workspace.py",
                "tests/test_structure.py",
            )
            tests(
                "17 authorized evidence / effects",
                ENGINEERING,
                "tests/test_authorized_effects.py",
                "tests/test_consumer_readiness.py",
            )
            tests(
                "18 M8 regressions",
                ENGINEERING,
                "tests/test_analyst.py",
                "tests/test_analyst_architecture.py",
                "tests/test_coding.py",
                "tests/test_coding_m4.py",
                "tests/test_coding_prompt.py",
                "tests/test_reviewer.py",
                "tests/test_json_document.py",
            )
            tests(
                "19 ForgeAI-1/2/3 replay regressions",
                FORGEAI,
                "tests/test_domain.py",
                "tests/test_worker.py",
                "tests/test_cli.py",
                "tests/test_architecture.py",
                "tests/test_review.py",
                "tests/test_rework.py",
            )
            tests(
                "20 LQ1 replay / local HTTP stubs",
                FORGEAI,
                "evaluation/tests",
                "--ignore=evaluation/tests/test_lq1_fixtures_docker.py",
                "--ignore=evaluation/tests/test_lq1_diagnostics_docker.py",
            )
            tests(
                "21 clean installed public consumer",
                ENGINEERING,
                "tests/test_structure_install.py",
            )
            project(
                "22 Engineering mypy",
                ENGINEERING,
                "mypy",
                "--cache-dir",
                str(temp / "mypy-e"),
                "src",
                "tests",
                "examples",
            )
            project(
                "22b ForgeAI mypy",
                FORGEAI,
                "mypy",
                "--cache-dir",
                str(temp / "mypy-f"),
                "src",
                "tests",
                "demo.py",
                "evaluation/forgeai_eval",
                "evaluation/tests",
                "evaluation/run.py",
            )
            run(
                "22c validator mypy",
                [
                    sys.executable,
                    "-m",
                    "mypy",
                    "--cache-dir",
                    str(temp / "mypy-v"),
                    str(Path(__file__)),
                ],
            )
            for label, cwd, targets in (
                ("Engineering", ENGINEERING, ("src", "tests", "examples")),
                ("ForgeAI", FORGEAI, ("src", "tests", "demo.py", "evaluation")),
            ):
                project(
                    "23 " + label + " Ruff lint",
                    cwd,
                    "ruff",
                    "check",
                    "--no-cache",
                    *targets,
                )
                project(
                    "24 " + label + " Ruff format",
                    cwd,
                    "ruff",
                    "format",
                    "--check",
                    "--no-cache",
                    *targets,
                )
            run(
                "23b validator lint",
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "check",
                    "--no-cache",
                    str(Path(__file__)),
                ],
            )
            run(
                "24b validator format",
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "format",
                    "--check",
                    "--no-cache",
                    str(Path(__file__)),
                ],
            )
            run("25 git diff check", ["git", "diff", "--check"])
        except Exception as error:
            for item in completed:
                print("PASS " + item)
            print(f"FAIL {phase}; later phases NOT RUN: {error}")
            return 1
    for item in completed:
        print("PASS " + item)
    print("DISCOVERY-1 LOCAL VALIDATION PASSED - no live model; no Docker required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
