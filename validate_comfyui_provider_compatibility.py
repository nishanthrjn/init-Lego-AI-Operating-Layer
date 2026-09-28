"""ComfyUI provider-compatibility validation; orchestration only.

Run from the repository root:

    uv run --locked python .\\validate_comfyui_provider_compatibility.py

Never runs `uv add`/`uv lock`/`uv sync`, installs or downloads anything, or
contacts Comfy Cloud or a live local ComfyUI. Every provider interaction is a
deterministic fake. Streams output, stops at the first failed phase and exits
non-zero on failure.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "packages" / "legoai-generative-media"
TESTS = PACKAGE / "tests"
EXAMPLES = [
    ROOT / "examples" / "comfyui-text-to-image",
    ROOT / "examples" / "generative-media-minimal",
]
SELF = ROOT / "validate_comfyui_provider_compatibility.py"
PINNED = {
    "legoai-reference": "0.1.0.dev0",
    "pytest": "9.1.1",
    "mypy": "2.3.1",
    "ruff": "0.16.8",
    "hatchling": "1.32.3",
    "editables": "0.5",
}


def main() -> int:
    uv = shutil.which("uv")
    git = shutil.which("git")
    python = sys.executable
    environment = os.environ.copy()
    paths = [str(PACKAGE / "src"), str(ROOT / "src"), str(TESTS)]
    environment["PYTHONPATH"] = os.pathsep.join(paths)
    environment["MYPYPATH"] = os.pathsep.join(paths)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    # Deterministic fakes only: no credential from the operator's shell is visible.
    environment.pop("COMFY_API_KEY", None)
    completed: list[str] = []
    phase = "environment"
    with tempfile.TemporaryDirectory(prefix="legoai-comfy-providers-") as temporary:

        def run(name: str, command: list[str]) -> None:
            nonlocal phase
            phase = name
            print("\n[PHASE] " + name, flush=True)
            print(subprocess.list2cmdline(command), flush=True)
            subprocess.run(command, cwd=ROOT, env=environment, check=True, shell=False)
            completed.append(name)

        def tests(name: str, *files: str) -> None:
            run(
                name,
                [
                    python,
                    "-m",
                    "pytest",
                    "-p",
                    "no:cacheprovider",
                    "--basetemp",
                    str(Path(temporary) / name.split()[0]),
                    "-q",
                    *[str(TESTS / f) for f in files],
                ],
            )

        try:
            phase = "1 environment / uv / Python"
            if uv is None:
                raise RuntimeError("uv is required: https://docs.astral.sh/uv/")
            if git is None:
                raise RuntimeError("git is required")
            expected = (ROOT / ".venv").resolve()
            if Path(sys.prefix).resolve() != expected:
                raise RuntimeError(
                    "run through the locked root environment: "
                    "uv run --locked python .\\validate_comfyui_provider_compatibility.py"
                )
            run(
                "1 environment / uv / Python",
                [
                    python,
                    "-c",
                    "import subprocess,sys; assert sys.version_info[:2] == (3,14), sys.version;"
                    f" print(sys.version); subprocess.run([{uv!r}, '--version'], check=True)",
                ],
            )
            run(
                "2 dependency integrity",
                [
                    python,
                    "-c",
                    "import importlib.metadata as m; expected="
                    + repr(PINNED)
                    + "; bad=[k for k,v in expected.items() if m.version(k)!=v];"
                    " assert not bad, bad; print('Locked toolchain verified; nothing installed')",
                ],
            )
            run(
                "3 typing",
                [
                    python,
                    "-m",
                    "mypy",
                    "--config-file",
                    str(PACKAGE / "pyproject.toml"),
                    "--cache-dir",
                    str(Path(temporary) / "mypy"),
                    str(PACKAGE / "src"),
                    str(TESTS),
                    *[str(e) for e in EXAMPLES],
                    str(SELF),
                ],
            )
            lint_targets = [str(PACKAGE), *[str(e) for e in EXAMPLES], str(SELF)]
            run(
                "4 ruff lint",
                [python, "-m", "ruff", "check", "--no-cache", *lint_targets],
            )
            run(
                "5 ruff format check",
                [
                    python,
                    "-m",
                    "ruff",
                    "format",
                    "--check",
                    "--no-cache",
                    *lint_targets,
                ],
            )
            tests("6 provider configuration", "test_provider_config.py")
            tests("7 discovery and driver selection", "test_discovery.py")
            tests(
                "8 legacy driver regression",
                "test_contracts.py",
                "test_adapter.py",
                "test_http.py",
                "test_policy.py",
            )
            tests("9 v2 driver", "test_driver_v2.py")
            tests("10 cloud/remote transport", "test_remote_transport.py")
            tests(
                "11 reconciliation and effects",
                "test_reconcile.py",
                "test_effects.py",
                "test_composition.py",
            )
            tests("12 application reuse", "test_reuse.py")
            tests("13 architecture and import boundaries", "test_architecture.py")
            wheel_dir = Path(temporary) / "wheel"
            wheel_dir.mkdir()
            build = (
                "from hatchling.builders.wheel import WheelBuilder; import sys;"
                " print(next(WheelBuilder(sys.argv[1]).build(directory=sys.argv[2])))"
            )
            run(
                "14a package build", [python, "-c", build, str(PACKAGE), str(wheel_dir)]
            )
            wheel = next(wheel_dir.glob("*.whl"))
            smoke = (
                "import sys,zipfile; sys.path.insert(0,sys.argv[1]);"
                " import legoai_generative_media.service as s,"
                " legoai_generative_media.drivers.v2 as d;"
                " assert sys.argv[1] in s.__file__ and sys.argv[1] in d.__file__;"
                " names=zipfile.ZipFile(sys.argv[1]).namelist();"
                " assert not any(n.startswith('legoai/') for n in names);"
                " assert any(n.endswith('drivers/legacy.py') for n in names);"
                " print('Built wheel imported without installation')"
            )
            run("14b package import", [python, "-c", smoke, str(wheel)])
            run(
                "15 affected existing checks",
                [
                    python,
                    "-m",
                    "pytest",
                    "-p",
                    "no:cacheprovider",
                    "--basetemp",
                    str(Path(temporary) / "existing"),
                    "-q",
                    "tests/integration/composition/test_model_governed.py",
                    "tests/architecture/test_import_boundaries.py",
                ],
            )
            run("16 git diff --check", [git, "diff", "--check"])
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
        "DETERMINISTIC PROVIDER VALIDATION PASSED - "
        "LIVE LOCAL/CLOUD QUALIFICATION REMAINS OPERATOR-RUN"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
