"""Maintainer-only offline pilot qualification. No Docker or external provider."""

import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path

from validate_forgeai_remote_model_profile_1 import LOCAL_TESTS, REMOTE_TESTS

ROOT = Path(__file__).resolve().parent
FORGEAI = ROOT / "examples/forgeai"
BASE = "7882ce96416cc55016142228122eb24395faf526"
SELF = "validate_forgeai_v0_2_kisski_bounded_live_pilot_1.py"
PILOT = "scripts/forgeai_kisski_bounded_live_pilot.py"
HELPER = "scripts/kisski_saia_qualification.py"
TEST = "examples/forgeai/tests/test_kisski_bounded_live_pilot.py"
PLAN = "planning/FORGEAI-V0.2-KISSKI-BOUNDED-LIVE-PILOT-1.md"
ALLOWED = frozenset({SELF, PILOT, HELPER, TEST, PLAN})


def existing_tooling(source: str) -> str:
    tree = ast.parse(source)
    tree.body = [
        node
        for node in tree.body
        if not (isinstance(node, ast.FunctionDef) and node.name == "discover_models")
    ]
    return ast.dump(tree, include_attributes=False)


def main() -> int:
    uv = shutil.which("uv")
    if uv is None:
        print("FAIL: existing locked uv environments required")
        return 1
    env = os.environ.copy()
    for name in (
        "VIRTUAL_ENV",
        "LEGOAI_QUALIFY_PROJECT_CHECKS",
        "LEGOAI_QUALIFY_FORGEAI_REMOTE",
        "LEGOAI_SANDBOX_CHECKS_IMAGE",
        "LEGOAI_QUALIFY_FORGEAI_V02_SANDBOX",
    ):
        env.pop(name, None)
    env["UV_OFFLINE"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    import_paths = (str(ROOT), str(FORGEAI), str(FORGEAI / "src"))
    env["PYTHONPATH"] = os.pathsep.join(import_paths)
    env["MYPYPATH"] = str(ROOT)
    phase = "exact tooling scope; production and frozen evidence preserved"

    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, encoding="utf-8"
        )

    def run(label: str, args: list[str], cwd: Path = ROOT) -> None:
        nonlocal phase
        phase = label
        print("\n[PHASE] " + label, flush=True)
        subprocess.run(args, cwd=cwd, env=env, check=True)

    def project(label: str, *args: str) -> None:
        assert uv is not None
        run(
            label,
            [uv, "run", "--locked", "--offline", "--no-sync", "python", *args],
            FORGEAI,
        )

    try:
        print("[PHASE] " + phase, flush=True)
        changed = set(
            (
                git("diff", "--name-only", BASE)
                + git("diff", "--cached", "--name-only", BASE)
                + git("ls-files", "--others", "--exclude-standard")
            ).splitlines()
        )
        if changed - ALLOWED:
            raise ValueError("outside pilot scope: " + repr(sorted(changed - ALLOWED)))
        original = existing_tooling(git("show", BASE + ":" + HELPER))
        if existing_tooling((ROOT / HELPER).read_text("utf-8")) != original:
            raise ValueError("existing qualification behavior changed")
        if HELPER in git("diff", "--cached", "--name-only", BASE).splitlines():
            if existing_tooling(git("show", ":" + HELPER)) != original:
                raise ValueError("staged qualification behavior changed")
        project(
            "inert plan",
            "-m",
            "scripts.forgeai_kisski_bounded_live_pilot",
            "--plan",
        )
        project(
            "fixture, admission, authorization, gates, reports and call ceilings",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests/test_kisski_bounded_live_pilot.py",
        )
        project(
            "bounded lifecycle and authority regressions; no Docker",
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "tests",
            "--ignore=tests/test_end_to_end.py",
            "--ignore=tests/test_clean_install.py",
            "--ignore=tests/test_kisski_bounded_live_pilot.py",
            "-k",
            "not real_docker and not real_sandbox",
        )
        for label, paths in (
            ("REMOTE custody/disclosure", REMOTE_TESTS),
            ("LOCAL preservation", LOCAL_TESTS),
            (
                "KiSSKI synthetic regressions",
                (
                    "scripts/tests/test_kisski_saia_qualification.py",
                    "scripts/tests/test_kisski_saia_receive_diagnostics.py",
                    "scripts/tests/test_kisski_saia_function_call_shapes.py",
                ),
            ),
            ("architecture boundaries", ("tests/architecture",)),
        ):
            run(
                label,
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
        targets = [str(ROOT / path) for path in (PILOT, TEST, HELPER, SELF)]
        project("typing tooling", "-m", "mypy", *targets)
        project(
            "lint tooling",
            "-m",
            "ruff",
            "check",
            "--no-cache",
            "--config",
            str(ROOT / "pyproject.toml"),
            "--config",
            'lint.isort.known-first-party = ["forgeai", "scripts", "examples", '
            '"validate_forgeai_remote_model_profile_1"]',
            "--config",
            'lint.isort.known-third-party = ["demo", "legoai", "legoai_engineering"]',
            *targets,
        )
        project(
            "format tooling",
            "-m",
            "ruff",
            "format",
            "--check",
            "--no-cache",
            *targets,
        )
        run("working whitespace", ["git", "diff", "--check", BASE])
        run("staged whitespace", ["git", "diff", "--cached", "--check"])
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL: {phase}: {type(error).__name__}; later phases NOT RUN")
        return 1
    print(
        "FORGEAI-V0.2-KISSKI-BOUNDED-LIVE-PILOT-1 HARNESS LOCALLY QUALIFIED; "
        "ATTENDED BOUNDED LIVE PILOT READY SUBJECT TO MODEL ADMISSION; "
        "NO LIVE PILOT EXECUTED; NO GLOBAL V0.2 OR DEPLOYMENT QUALIFICATION; "
        "PILOT_MODEL_NOT_ADMITTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
