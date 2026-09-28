"""Read-only source validation orchestration; never installs or contacts ComfyUI."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "packages" / "legoai-generative-media"
EXAMPLE = ROOT / "examples" / "comfyui-text-to-image"


def main() -> int:
    python = (
        ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    if not python.is_file():
        print("Root development environment missing. Explicit setup: uv sync --locked")
        return 1
    git = shutil.which("git")
    if git is None:
        print("Git is required.")
        return 1
    environment = os.environ.copy()
    paths = [str(PACKAGE / "src"), str(ROOT / "src"), str(PACKAGE / "tests")]
    environment["PYTHONPATH"] = os.pathsep.join(paths)
    environment["MYPYPATH"] = os.pathsep.join(paths)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed: list[str] = []
    phase = "environment"
    with tempfile.TemporaryDirectory(prefix="legoai-comfyui-validation-") as temporary:

        def run(name: str, command: list[str], cwd: Path = ROOT) -> None:
            nonlocal phase
            phase = name
            print("\n[PHASE] " + name, flush=True)
            print(subprocess.list2cmdline(command), flush=True)
            subprocess.run(command, cwd=cwd, env=environment, check=True, shell=False)
            completed.append(name)

        def tests(name: str, *files: str) -> None:
            run(
                name,
                [
                    str(python),
                    "-m",
                    "pytest",
                    "-p",
                    "no:cacheprovider",
                    "--basetemp",
                    str(Path(temporary) / name),
                    "-q",
                    *[str(PACKAGE / "tests" / f) for f in files],
                ],
            )

        try:
            run(
                "1 environment",
                [
                    str(python),
                    "-c",
                    "import sys; assert sys.version_info[:2] == (3,14); print(sys.version)",
                ],
            )
            run(
                "2 dependency integrity",
                [
                    str(python),
                    "-c",
                    "import importlib.metadata as m; expected={'legoai-reference':'0.1.0.dev0','pytest':'9.1.1','mypy':'2.3.1','ruff':'0.16.8','hatchling':'1.32.3','editables':'0.5'}; [(_ for _ in ()).throw(RuntimeError(k+' version mismatch')) for k,v in expected.items() if m.version(k)!=v]; print('Existing root toolchain verified; no installation performed')",
                ],
            )
            run(
                "3 typing",
                [
                    str(python),
                    "-m",
                    "mypy",
                    "--config-file",
                    str(PACKAGE / "pyproject.toml"),
                    "--cache-dir",
                    str(Path(temporary) / "mypy"),
                    str(PACKAGE / "src"),
                    str(PACKAGE / "tests"),
                    str(EXAMPLE),
                    str(ROOT / "validate_comfyui_text_to_image.py"),
                ],
            )
            run(
                "4 lint",
                [
                    str(python),
                    "-m",
                    "ruff",
                    "check",
                    "--no-cache",
                    str(PACKAGE),
                    str(EXAMPLE),
                    str(ROOT / "validate_comfyui_text_to_image.py"),
                ],
            )
            tests("5 contracts", "test_contracts.py")
            tests("6 transport", "test_adapter.py", "test_http.py")
            tests("7 effects", "test_effects.py", "test_composition.py")
            # Completion policy, simulated long jobs, reconciliation with zero
            # submissions and UNKNOWN -> COMPLETED knowledge refinement.
            tests("7b policy and reconciliation", "test_policy.py", "test_reconcile.py")
            tests("8 architecture", "test_architecture.py")
            wheel_dir = Path(temporary) / "wheel"
            wheel_dir.mkdir()
            build_code = "from hatchling.builders.wheel import WheelBuilder; import sys; print(next(WheelBuilder(sys.argv[1]).build(directory=sys.argv[2])))"
            run(
                "9a wheel build",
                [str(python), "-c", build_code, str(PACKAGE), str(wheel_dir)],
            )
            wheel = next(wheel_dir.glob("*.whl"))
            import_code = "import sys,zipfile; sys.path.insert(0,sys.argv[1]); import legoai_generative_media.values as v; assert sys.argv[1] in v.__file__; v.TextToImageRequest('wheel smoke'); z=zipfile.ZipFile(sys.argv[1]); assert not any(n.startswith('legoai/') for n in z.namelist()); print('Built wheel imported without installation')"
            run("9b wheel import", [str(python), "-c", import_code, str(wheel)])
            run(
                "10 affected existing checks",
                [
                    str(python),
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
            run("11 git diff", [git, "diff", "--check"])
        except Exception as error:
            for item in completed:
                print("PASS " + item)
            print("FAIL " + phase + "; later phases NOT RUN")
            if isinstance(error, subprocess.CalledProcessError):
                return error.returncode if error.returncode > 0 else 1
            return 1
    for item in completed:
        print("PASS " + item)
    print("DETERMINISTIC VALIDATION PASSED - LIVE COMFYUI QUALIFICATION STILL REQUIRED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
