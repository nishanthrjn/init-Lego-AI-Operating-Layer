"""Fresh-environment install of ForgeAI plus its LegoAI wheels; demo outside the
checkout. Runs the real Docker sandbox (Windows + Docker Desktop scope)."""

import ast
import os
import shutil
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1]
REPOSITORY = PACKAGE.parents[1]

pytestmark = pytest.mark.skipif(
    os.name != "nt", reason="Windows Desktop reference scope"
)


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, timeout=300, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def build(project: Path, artifacts: Path) -> Path:
    run(
        ["uv", "build", "--no-build-isolation", "--wheel", "--out-dir", str(artifacts)],
        project,
    )
    return artifacts


def test_clean_install_runs_the_fixture_task_outside_the_checkout(
    tmp_path: Path,
) -> None:
    wheels = tmp_path / "wheels"
    for project in (
        REPOSITORY,
        REPOSITORY / "packages" / "legoai-engineering",
        PACKAGE,
    ):
        build(project, wheels)
    forgeai_wheel = next(wheels.glob("forgeai-*.whl"))
    with zipfile.ZipFile(forgeai_wheel) as wheel:
        names = {n for n in wheel.namelist() if ".dist-info/" not in n}
        assert names == {
            f"forgeai/{m}.py"
            for m in ("__init__", "domain", "guard", "worker", "composition", "cli")
        }
        metadata = wheel.read(
            next(n for n in wheel.namelist() if n.endswith("METADATA"))
        ).decode()
        entry_points = wheel.read(
            next(n for n in wheel.namelist() if n.endswith("entry_points.txt"))
        ).decode()
    requires = sorted(
        line for line in metadata.splitlines() if line.startswith("Requires-Dist:")
    )
    assert requires == [
        "Requires-Dist: legoai-engineering[analyst]==0.1.0.dev0",
        "Requires-Dist: legoai-reference==0.1.0.dev0",
    ]
    assert "forgeai = forgeai.cli:main" in entry_points

    environment = tmp_path / "installed"
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / "Scripts" / "python.exe"
    run(
        ["uv", "pip", "install", "--python", str(python), "--offline", "--no-deps"]
        + [str(w) for w in sorted(wheels.glob("*.whl"))],
        tmp_path,
    )
    # The installed ForgeAI sources import only public LegoAI modules.
    site = environment / "Lib" / "site-packages" / "forgeai"
    for path in site.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(p.startswith("_") for p in node.module.split("."))
                assert not node.module.startswith("legoai.reference")

    application = tmp_path / "application"
    application.mkdir()
    shutil.copy2(PACKAGE / "demo.py", application / "demo.py")
    shutil.copytree(PACKAGE / "fixtures", application / "fixtures")
    probe = run(
        [str(python), "-I", "-c", "import forgeai, sys; print(forgeai.__file__)"],
        application,
    )
    assert Path(probe.stdout.strip()).is_relative_to(environment)
    # -I: no checkout, no PYTHONPATH, no user site; only the installed wheels.
    result = run([str(python), "-I", str(application / "demo.py")], application)
    lines = result.stdout.splitlines()
    assert lines[0] == "disposition: succeeded", result.stdout
    assert "changed files: src/inventory/stock.py, tests/test_stock.py" in lines
    assert "check ruff_check: passed" in lines
    assert "check mypy: passed" in lines
    assert "check pytest: passed" in lines
    assert any(line.startswith("final HEAD: unchanged") for line in lines)
    assert (environment / "Scripts" / "forgeai.exe").is_file()
    assert sys.prefix != str(environment)
