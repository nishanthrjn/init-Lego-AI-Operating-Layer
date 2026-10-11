"""Offline audit checks; no dependency acquisition or live qualification.

Existing wheel-isolation tests install only a locally built wheel in temporary
environments. This script does not install dependencies or launch live providers.
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "25f847cae3961f63372391072695d919e3ad1927"
REPORT = "planning/LEGOAI-ARCHITECTURE-DESIGN-CONFORMANCE-AUDIT-1"
TEST = "tests/architecture/test_consumer_private_boundaries.py"
PACKAGING_TEST = "tests/architecture/test_package_install.py"
SOURCE = "src/legoai/runtime/_composition/disclosure.py"
ALLOWED = {
    "AGENTS.md",
    "CLAUDE.md",
    ".agents/skills/engineering-implementation/SKILL.md",
    ".claude/skills/engineering-implementation/SKILL.md",
    "packages/legoai-document/README.md",
    "examples/assessment_starter/README.md",
    REPORT + ".md",
    REPORT + "-private-imports.tsv",
    TEST,
    PACKAGING_TEST,
    SOURCE,
    Path(__file__).name,
}


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    ).stdout


def executable_tree(source: str) -> str:
    tree = ast.parse(source)
    if ast.get_docstring(tree) is not None:
        tree.body.pop(0)
    return ast.dump(tree, include_attributes=False)


def boundaries() -> None:
    changed = set(git("diff", BASELINE, "--name-only").splitlines())
    changed.update(git("ls-files", "--others", "--exclude-standard").splitlines())
    if changed - ALLOWED:
        raise ValueError(f"outside audit scope: {sorted(changed - ALLOWED)}")
    old = git("show", f"{BASELINE}:{SOURCE}")
    new = (ROOT / SOURCE).read_text(encoding="utf-8")
    if executable_tree(old) != executable_tree(new):
        raise ValueError("runtime change must remain module-docstring-only")
    policy = ROOT / "AGENTS.md"
    workflow = ROOT / ".agents/skills/engineering-implementation/SKILL.md"
    for name, required in (
        ("CLAUDE.md", {policy, workflow}),
        (".claude/skills/engineering-implementation/SKILL.md", {policy, workflow}),
        (".agents/skills/engineering-implementation/SKILL.md", {policy}),
    ):
        path = ROOT / name
        links = {
            (path.parent / target).resolve()
            for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8"))
        }
        if not required <= links or any(not target.is_file() for target in links):
            raise ValueError(f"shared policy/workflow reference missing: {name}")


def run(
    phase: str,
    command: list[str],
    environment: dict[str, str],
    cwd: Path = ROOT,
) -> None:
    print(f"\n[PHASE] {phase}", flush=True)
    subprocess.run(command, cwd=cwd, env=environment, check=True, timeout=900)


def main() -> int:
    environment = dict(os.environ)
    paths = [
        "src",
        "packages/legoai-engineering/src",
        "packages/legoai-engineering/examples",
        "packages/legoai-generative-media/src",
        "packages/legoai-generative-media/tests",
        "packages/legoai-document/src",
        "examples/forgeai/src",
        "examples/documind/src",
    ]
    environment["PYTHONPATH"] = os.pathsep.join(str(ROOT / path) for path in paths)
    environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    environment["UV_OFFLINE"] = "1"
    environment["PIP_NO_INDEX"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        print("[PHASE] audit scope, unchanged runtime AST and shared instructions")
        boundaries()
        engineering = ROOT / "packages/legoai-engineering"
        executable = "Scripts/python.exe" if os.name == "nt" else "bin/python"
        engineering_python = engineering / ".venv" / executable
        if not engineering_python.is_file():
            raise ValueError("existing Engineering .venv required; nothing installed")
        run(
            "Core and consumer architecture; allowed/forbidden fitness controls",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/architecture",
                "packages/legoai-document/tests/architecture",
                "packages/legoai-generative-media/tests/test_architecture.py",
                "examples/forgeai/tests/test_architecture.py",
            ],
            environment,
        )
        run(
            "Engineering architecture and deterministic effect authorization",
            [
                str(engineering_python),
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/test_architecture.py",
                "tests/test_authorized_effects.py",
                "tests/test_consumer_readiness.py",
            ],
            environment,
            engineering,
        )
        run(
            "deterministic public host and VTO effect truth",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "examples/documind/tests/unit/test_public_composition.py",
                "packages/legoai-generative-media/tests/test_tryon_composition.py",
            ],
            environment,
        )
        files = [TEST, PACKAGING_TEST, SOURCE, Path(__file__).name]
        for phase, command in (
            ("typing", ["mypy", *files]),
            ("lint", ["ruff", "check", *files]),
            ("format", ["ruff", "format", "--check", *files]),
        ):
            run(phase, [sys.executable, "-m", *command], environment)
        run("working whitespace", ["git", "diff", "--check"], environment)
        run("staged whitespace", ["git", "diff", "--cached", "--check"], environment)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"FAIL: {type(error).__name__}: {error}; later phases NOT RUN")
        return 1
    print(
        "LEGOAI-ARCHITECTURE-DESIGN-CONFORMANCE-AUDIT-1 LOCAL CHECKS PASSED; "
        "RECORDED DEBT REMAINS; NO LIVE OR GLOBAL CONFORMANCE QUALIFIED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
