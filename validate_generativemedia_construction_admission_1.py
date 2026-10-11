"""Maintainer-run M-04 checks: deterministic fakes only; no provider acquisition."""

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "5b027ccad9951e0afe8fd7f2f310b71dd508e46b"
PACKAGE = "packages/legoai-generative-media"
SERVICE = f"{PACKAGE}/src/legoai_generative_media/service.py"
TEST = f"{PACKAGE}/tests/test_tryon_reuse.py"
SELF = "validate_generativemedia_construction_admission_1.py"
ALLOWED = frozenset({SERVICE, TEST, f"{PACKAGE}/README.md", SELF})
TARGETS = [SERVICE, TEST, SELF]


def git_paths(args: list[str]) -> set[str]:
    output = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, timeout=30
    ).stdout
    return {item.decode("utf-8") for item in output.split(b"\0") if item}


def unaffected_service(source: str) -> str:
    tree = ast.parse(source)
    tree.body = [
        node
        for node in tree.body
        if not (
            isinstance(node, ast.AsyncFunctionDef) and node.name == "open_virtual_try_on"
        )
        and not (
            isinstance(node, ast.ImportFrom)
            and node.module == "legoai.kernel.errors"
            and [(alias.name, alias.asname) for alias in node.names]
            == [("ErrorCategory", None)]
        )
    ]
    return ast.dump(tree, include_attributes=False)


def check_scope() -> None:
    changed = git_paths(["diff", "--name-only", "--no-renames", "-z", BASELINE, "--"])
    changed |= git_paths(
        ["diff", "--cached", "--name-only", "--no-renames", "-z", BASELINE, "--"]
    )
    changed |= git_paths(["ls-files", "--others", "--exclude-standard", "-z"])
    if changed - ALLOWED:
        raise ValueError(f"changes outside M-04 scope: {sorted(changed - ALLOWED)}")
    for name in ALLOWED:
        if (ROOT / name).is_symlink() or not (ROOT / name).is_file():
            raise ValueError(f"missing or symlinked slice file: {name}")
    old = subprocess.run(
        ["git", "show", f"{BASELINE}:{SERVICE}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout.decode("utf-8")
    staged = subprocess.run(
        ["git", "show", f":{SERVICE}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout.decode("utf-8")
    for source in ((ROOT / SERVICE).read_text(encoding="utf-8"), staged):
        if unaffected_service(old) != unaffected_service(source):
            raise ValueError("service behavior outside VTO construction changed")


def main() -> int:
    phase = "M-04-only scope; Core, Secret and ADRs unchanged"
    try:
        print(f"[PHASE] {phase}", flush=True)
        check_scope()
        environment = os.environ.copy()
        search = [ROOT / PACKAGE / "src", ROOT / "src", ROOT / PACKAGE / "tests"]
        environment["PYTHONPATH"] = os.pathsep.join(map(str, search))
        environment["MYPYPATH"] = environment["PYTHONPATH"]
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        environment.pop("COMFY_API_KEY", None)
        environment.pop("PYTEST_ADDOPTS", None)
        with tempfile.TemporaryDirectory(prefix="media-m04-") as temporary:

            def run(label: str, args: list[str]) -> None:
                nonlocal phase
                phase = label
                print(f"\n[PHASE] {phase}", flush=True)
                subprocess.run(args, cwd=ROOT, env=environment, check=True, timeout=600)

            def tests(label: str, files: list[str]) -> None:
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
                        *files,
                    ],
                )

            tests("construction ordering and positive controls", [TEST])
            tests(
                "media configuration and explicit diagnostics",
                [
                    f"{PACKAGE}/tests/{name}.py"
                    for name in (
                        "test_provider_config",
                        "test_discovery",
                        "test_driver_v2",
                        "test_reuse",
                    )
                ],
            )
            tests(
                "VTO deterministic effects and reconciliation",
                [
                    f"{PACKAGE}/tests/{name}.py"
                    for name in (
                        "test_tryon_contract",
                        "test_tryon_workflow",
                        "test_tryon_preflight",
                        "test_tryon_geometry",
                        "test_tryon_effects",
                        "test_tryon_composition",
                        "test_tryon_reconcile",
                        "test_tryon_live_tooling",
                        "test_input_disclosure",
                    )
                ],
            )
            # Deliberately exclude socket-based transport tests and any runtime
            # launch/integration suite. These architecture tests inspect source.
            tests(
                "architecture and private boundary controls",
                [
                    f"{PACKAGE}/tests/test_architecture.py",
                    "tests/architecture/test_consumer_private_boundaries.py",
                ],
            )
            run(
                "typing",
                [
                    sys.executable,
                    "-m",
                    "mypy",
                    "--config-file",
                    f"{PACKAGE}/pyproject.toml",
                    "--cache-dir",
                    str(Path(temporary) / "mypy"),
                    *TARGETS,
                ],
            )
            run("lint", [sys.executable, "-m", "ruff", "check", "--no-cache", *TARGETS])
            run(
                "format",
                [sys.executable, "-m", "ruff", "format", "--check", "--no-cache", *TARGETS],
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
        "GENERATIVE-MEDIA-CONSTRUCTION-ADMISSION-1 M-04 LOCALLY QUALIFIED; "
        "H-01 AND M-01 OPEN; ADR-027 PROPOSED; NO LIVE OR CREDENTIALED MEDIA QUALIFIED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
