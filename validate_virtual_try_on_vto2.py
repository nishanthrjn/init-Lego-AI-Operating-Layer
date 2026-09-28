"""VTO-2 validation: provider-neutral virtual try-on; orchestration only.

Run from the repository root:

    uv run python .\\validate_virtual_try_on_vto2.py

(`uv run --locked ...` additionally refuses a drifted lockfile.) Never adds or
installs dependencies, downloads models, needs CUDA, contacts ComfyUI or Comfy
Cloud, or uses real images: every PNG is synthetic and every provider is a
fake. Streams output, stops at the first failed phase, exits non-zero on
failure.
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
    ROOT / "examples" / "virtual-try-on",
    ROOT / "examples" / "virtual-try-on-minimal",
]
SELF = ROOT / "validate_virtual_try_on_vto2.py"
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
    with tempfile.TemporaryDirectory(prefix="legoai-vto2-") as temporary:

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
            if Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
                raise RuntimeError(
                    "run through the locked root environment: "
                    "uv run python .\\validate_virtual_try_on_vto2.py"
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
            tests("6 TryOnRequest / Port contract", "test_tryon_contract.py")
            tests("7 preflight before disclosure", "test_tryon_preflight.py")
            tests("8 try-on workflow shape/digest", "test_tryon_workflow.py")
            tests("9 upload + submission composition", "test_tryon_composition.py")
            tests("10 effect/disclosure", "test_tryon_effects.py")
            tests("11 output geometry", "test_tryon_geometry.py")
            tests("12 reconciliation", "test_tryon_reconcile.py", "test_reconcile.py")
            tests("13 N-application reuse", "test_tryon_reuse.py", "test_reuse.py")
            tests("14 architecture and import boundaries", "test_architecture.py")
            wheel_dir = Path(temporary) / "wheel"
            wheel_dir.mkdir()
            build = (
                "from hatchling.builders.wheel import WheelBuilder; import sys;"
                " print(next(WheelBuilder(sys.argv[1]).build(directory=sys.argv[2])))"
            )
            run(
                "15a package build",
                [python, "-c", build, str(PACKAGE), str(wheel_dir)],
            )
            wheel = next(wheel_dir.glob("*.whl"))
            smoke = (
                "import sys,zipfile; sys.path.insert(0,sys.argv[1]);"
                " import legoai_generative_media.virtual_try_on as a,"
                " legoai_generative_media.tryon as t,"
                " legoai_generative_media.ports as p;"
                " assert sys.argv[1] in a.__file__ and sys.argv[1] in t.__file__;"
                " names=zipfile.ZipFile(sys.argv[1]).namelist();"
                " assert not any(n.startswith('legoai/') for n in names);"
                " assert p.VirtualTryOnPort and t.WIDTH == 768 and t.HEIGHT == 1024;"
                " print('Built wheel imported without installation')"
            )
            run("15b package import", [python, "-c", smoke, str(wheel)])
            tests(
                "16 VTO-1 regressions",
                "test_image_input.py",
                "test_png_strip.py",
                "test_input_disclosure.py",
                "test_upload_transport.py",
                "test_input_policy.py",
            )
            tests(
                "17 provider-compatibility regressions",
                "test_provider_config.py",
                "test_discovery.py",
                "test_driver_v2.py",
                "test_remote_transport.py",
            )
            tests(
                "18 affected generative-media tests",
                "test_contracts.py",
                "test_adapter.py",
                "test_http.py",
                "test_policy.py",
                "test_effects.py",
                "test_composition.py",
            )
            run("19 git diff --check", [git, "diff", "--check"])
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
        "VTO-2 DETERMINISTIC VALIDATION PASSED - "
        "NO LIVE COMFYUI, CUDA, MODELS OR REAL IMAGES USED; VTO-3 PENDING"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
