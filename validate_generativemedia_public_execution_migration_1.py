"""Maintainer-only offline qualification of the media public facade migration."""

import ast
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "9dae5680f8f86e92c5056534a2e2cee0416b8cd3"
PACKAGE = "packages/legoai-generative-media"
SOURCE = f"{PACKAGE}/src/legoai_generative_media"
SELF = "validate_generativemedia_public_execution_migration_1.py"
TARGETS = (
    [
        f"{SOURCE}/{name}.py"
        for name in ("local_host", "composition", "service", "values")
    ]
    + [
        f"{PACKAGE}/tests/{name}.py"
        for name in (
            "test_composition",
            "test_policy",
            "test_tryon_effects",
            "test_tryon_reuse",
            "test_public_execution",
        )
    ]
    + [
        "tests/architecture/test_consumer_private_boundaries.py",
        "tests/architecture/test_local_host.py",
        SELF,
    ]
)
MIGRATION_REASONS = {"media_execution_refused", "media_execution_unsettled"}
ALLOWED = frozenset(
    TARGETS
    + [
        f"{PACKAGE}/README.md",
        "docs/ports-and-adapters.md",
        "docs/modules/MODULE-CATALOG.md",
        "planning/GENERATIVE-MEDIA-PUBLIC-EXECUTION-MIGRATION-1.md",
    ]
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout.decode("utf-8")


def service_boundary(source: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name in {
            "TextToImageService",
            "TryOnService",
        }:
            for method in node.body:
                if isinstance(method, ast.AsyncFunctionDef) and method.name in {
                    "generate",
                    "try_on",
                }:
                    method.body = []  # Keep signatures, fields and other operations.
    return ast.dump(tree, include_attributes=False)


def values_boundary(source: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "REASONS"
        ):
            for item in ast.walk(node.value):
                if isinstance(item, ast.Set):
                    item.elts = [
                        entry
                        for entry in item.elts
                        if not (
                            isinstance(entry, ast.Constant)
                            and entry.value in MIGRATION_REASONS
                        )
                    ]
    return ast.dump(tree, include_attributes=False)


def check_scope() -> None:
    changed = set(
        git("diff", "--name-only", "--no-renames", "-z", BASELINE, "--").split("\0")
    )
    changed.update(
        git("diff", "--cached", "--name-only", "-z", BASELINE, "--").split("\0")
    )
    changed.update(git("ls-files", "--others", "--exclude-standard", "-z").split("\0"))
    changed.discard("")
    if changed - ALLOWED:
        raise ValueError(f"outside migration scope: {sorted(changed - ALLOWED)}")
    for name in ALLOWED:
        if not (ROOT / name).is_file() or (ROOT / name).is_symlink():
            raise ValueError(f"missing or symlinked slice file: {name}")
    for name, boundary in (
        (f"{SOURCE}/service.py", service_boundary),
        (f"{SOURCE}/values.py", values_boundary),
    ):
        baseline = boundary(git("show", f"{BASELINE}:{name}"))
        for source in (
            (ROOT / name).read_text(encoding="utf-8"),
            git("show", f":{name}"),
        ):
            if boundary(source) != baseline:
                raise ValueError(f"public/diagnostic/provider boundary changed: {name}")


WHEEL_SMOKE = """
import asyncio
from pathlib import Path
import legoai
import legoai_generative_media
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory
from legoai_generative_media.composition import invoke
from legoai_generative_media.local_host import prepare_local
from legoai_generative_media.values import (
    ApprovedWorkflowRef, GenerationResult, Outcome, TextToImageRequest,
)
assert Path(legoai.__file__).is_relative_to(Path(__import__('sys').prefix))
assert Path(legoai_generative_media.__file__).is_relative_to(
    Path(__import__('sys').prefix)
)
class Owner:
    async def generate(self, request):
        return GenerationResult(
            Outcome.FAILED, EffectExtent.NONE, error=ErrorCategory.VALIDATION_ERROR
        )
async def scenario():
    async with await prepare_local(
        Owner(), 'wheel', approved=ApprovedWorkflowRef('wheel', '1', '0' * 64)
    ) as session:
        execution, result = await invoke(
            session.execution, session.ready, session.context,
            session.contribution, session.contribution.revision,
            TextToImageRequest('synthetic'),
        )
        assert execution.effect is result.effect is EffectExtent.NONE
    assert await session.execution.close() == ()
asyncio.run(scenario())
"""


def main() -> int:
    phase = "migration scope; Core, providers, credentials and ADRs unchanged"
    try:
        print(f"[PHASE] {phase}", flush=True)
        check_scope()
        environment = os.environ.copy()
        search = [ROOT / PACKAGE / "src", ROOT / "src", ROOT / PACKAGE / "tests"]
        environment["PYTHONPATH"] = os.pathsep.join(map(str, search))
        environment["MYPYPATH"] = environment["PYTHONPATH"]
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        environment["UV_OFFLINE"] = "1"
        environment["UV_PYTHON"] = sys.executable
        environment.pop("PYTEST_ADDOPTS", None)
        environment.pop("COMFY_API_KEY", None)
        with tempfile.TemporaryDirectory(prefix="media-public-execution-") as temporary:
            scratch = Path(temporary)

            def run(label: str, args: list[str], cwd: Path = ROOT) -> None:
                nonlocal phase
                phase = label
                print(f"\n[PHASE] {phase}", flush=True)
                subprocess.run(args, cwd=cwd, env=environment, check=True, timeout=600)

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
                        str(scratch / label.split()[0]),
                        *files,
                    ],
                )

            tests(
                "architecture private boundaries and public controls",
                [
                    "tests/architecture/test_consumer_private_boundaries.py",
                    "tests/architecture/test_local_host.py",
                    "tests/architecture/test_governed_execution.py",
                    f"{PACKAGE}/tests/test_architecture.py",
                ],
            )
            tests(
                "media facade, custody, cancellation and public signatures",
                [
                    f"{PACKAGE}/tests/test_public_execution.py",
                    f"{PACKAGE}/tests/test_composition.py",
                ],
            )
            tests(
                "text deterministic effects, reconciliation and diagnostics",
                [
                    f"{PACKAGE}/tests/{name}.py"
                    for name in (
                        "test_adapter",
                        "test_contracts",
                        "test_policy",
                        "test_effects",
                        "test_reconcile",
                        "test_reuse",
                        "test_provider_config",
                        "test_discovery",
                        "test_driver_v2",
                    )
                ],
            )
            tests(
                "VTO M-04, effects, reconciliation and diagnostics",
                [
                    f"{PACKAGE}/tests/{name}.py"
                    for name in (
                        "test_tryon_reuse",
                        "test_tryon_contract",
                        "test_tryon_workflow",
                        "test_tryon_preflight",
                        "test_tryon_geometry",
                        "test_tryon_effects",
                        "test_tryon_composition",
                        "test_tryon_reconcile",
                        "test_tryon_live_tooling",
                        "test_input_disclosure",
                        "test_input_policy",
                    )
                ],
            )
            tests(
                "Core public execution contracts",
                ["tests/integration/composition/test_governed_execution.py"],
            )
            artifacts = scratch / "wheels"
            for project in (ROOT, ROOT / PACKAGE):
                run(
                    "offline wheel build " + project.name,
                    [
                        "uv",
                        "build",
                        "--offline",
                        "--no-build-isolation",
                        "--wheel",
                        "--out-dir",
                        str(artifacts),
                        str(project),
                    ],
                )
            phase = "fresh isolated environment"
            print(f"\n[PHASE] {phase}", flush=True)
            isolated = scratch / "isolated"
            venv.EnvBuilder(with_pip=False).create(isolated)
            python = isolated / (
                "Scripts/python.exe" if os.name == "nt" else "bin/python"
            )
            wheels = sorted(artifacts.glob("*.whl"))
            if len(wheels) != 2:
                raise ValueError("exact Core and media wheels required")
            run(
                "offline wheel installation without dependency acquisition",
                [
                    "uv",
                    "pip",
                    "install",
                    "--offline",
                    "--no-deps",
                    "--python",
                    str(python),
                    *map(str, wheels),
                ],
            )
            run(
                "installed wheel media invocation; synthetic owner only",
                [str(python), "-I", "-c", WHEEL_SMOKE],
                scratch,
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
                    str(scratch / "mypy"),
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
        "GENERATIVE-MEDIA-PUBLIC-EXECUTION-MIGRATION-1 LOCALLY QUALIFIED; "
        "M-01 CLOSED; H-01 OPEN; ADR-027 PROPOSED; "
        "NO LIVE OR CREDENTIALED MEDIA QUALIFIED; REMOTE VTO UNSUPPORTED"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
