"""Maintainer-only offline ADR-026 qualification; no live execution authority."""

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "36eee7fdede2e3669e52497d3fa7c853c279d01e"
PRODUCTION = (
    "src/legoai/runtime/api.py",
    "src/legoai/runtime/local.py",
    "src/legoai/reference/execution.py",
)
TESTS = (
    "tests/integration/composition/test_governed_execution.py",
    "tests/architecture/test_governed_execution.py",
    "tests/architecture/test_local_host.py",
    "tests/architecture/test_package_install.py",
)
SELF = "validate_governed_execution_public_facade_1.py"
TARGETS = (*PRODUCTION, *TESTS, SELF)
ALLOWED = frozenset((*TARGETS, "docs/ports-and-adapters.md"))


def git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, timeout=30
    ).stdout


def declarations(source: str) -> dict[str, str]:
    """Existing implementation bodies must remain unchanged, not just tests."""
    return {
        node.name: ast.dump(node, include_attributes=False)
        for node in ast.parse(source).body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name != "HostFailure"
    }


def check_scope() -> None:
    changed: set[str] = set()
    for args in (
        ("diff", "--name-only", "--no-renames", "-z", BASELINE, "--"),
        ("diff", "--cached", "--name-only", "--no-renames", "-z", BASELINE, "--"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ):
        changed.update(item.decode("utf-8") for item in git(*args).split(b"\0") if item)
    if changed - ALLOWED:
        raise ValueError(f"outside facade scope: {sorted(changed - ALLOWED)}")
    for name in ALLOWED:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"missing or symlinked slice file: {name}")
    for name in PRODUCTION:
        original = declarations(git("show", f"{BASELINE}:{name}").decode("utf-8"))
        for source in (
            (ROOT / name).read_text(encoding="utf-8"),
            git("show", f":{name}").decode("utf-8"),
        ):
            current = declarations(source)
            if any(current.get(key) != value for key, value in original.items()):
                raise ValueError(f"existing implementation changed: {name}")


def main() -> int:
    phase = "facade-only scope; existing Model, media, Secret and ADRs preserved"
    try:
        print(f"[PHASE] {phase}", flush=True)
        check_scope()
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        environment["UV_OFFLINE"] = "1"
        environment["PIP_NO_INDEX"] = "1"
        environment["PYTHONPATH"] = str(ROOT / "src")
        environment["MYPYPATH"] = str(ROOT / "src")
        environment.pop("PYTEST_ADDOPTS", None)
        with tempfile.TemporaryDirectory(prefix="governed-facade-") as temporary:

            def run(label: str, args: list[str]) -> None:
                nonlocal phase
                phase = label
                print(f"\n[PHASE] {phase}", flush=True)
                subprocess.run(args, cwd=ROOT, env=environment, check=True, timeout=600)

            def tests(label: str, paths: list[str]) -> None:
                run(
                    label,
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "-q",
                        "-p",
                        "no:cacheprovider",
                        "--basetemp",
                        str(Path(temporary) / label.split()[0]),
                        *paths,
                    ],
                )

            tests("facade contracts and two independent owners", [TESTS[0]])
            tests(
                "architecture and public/private controls",
                ["tests/architecture", "--ignore=" + TESTS[3]],
            )
            tests(
                "Model public host and invoking-plane regressions",
                [
                    "tests/integration/composition/test_local_host.py",
                    "tests/integration/composition/test_model_governed.py",
                    "tests/integration/composition/test_model_selection.py",
                    "tests/integration/composition/test_agent.py",
                ],
            )
            tests(
                "Core execution governance lifecycle and catalog",
                [
                    "tests/unit/execution",
                    "tests/unit/governance/test_context.py",
                    "tests/unit/reference/test_execution.py",
                    "tests/unit/reference/test_coordinator.py",
                    "tests/unit/reference/test_governance_registries.py",
                    "tests/unit/reference/test_static_security_context_registry.py",
                    "tests/unit/reference/test_plugins.py",
                    "tests/contract/test_catalog.py",
                    "tests/unit/reference/test_resolution.py",
                ],
            )
            tests("package offline build and fresh-wheel isolation", [TESTS[3]])
            run(
                "typing",
                [
                    sys.executable,
                    "-m",
                    "mypy",
                    "--cache-dir",
                    str(Path(temporary) / "mypy"),
                    *TARGETS,
                ],
            )
            run("lint", [sys.executable, "-m", "ruff", "check", "--no-cache", *TARGETS])
            run(
                "format",
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "format",
                    "--check",
                    "--no-cache",
                    *TARGETS,
                ],
            )
            run("working whitespace", ["git", "diff", "--check", BASELINE, "--"])
            run(
                "staged whitespace",
                ["git", "diff", "--cached", "--check", BASELINE, "--"],
            )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {phase}: {exc}; later phases NOT RUN")
        return 1
    print(
        "GOVERNED-EXECUTION-PUBLIC-FACADE-1 LOCALLY QUALIFIED; "
        "M-01 AND H-01 OPEN; ADR-027 PROPOSED; "
        "NO MEDIA MIGRATION OR LIVE PROVIDER QUALIFICATION"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
