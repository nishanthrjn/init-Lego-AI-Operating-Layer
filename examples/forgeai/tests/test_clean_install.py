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


def run(
    args: list[str], cwd: Path, answers: str | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
        input=answers,
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
            for m in (
                "__init__",
                "domain",
                "guard",
                "review",
                "worker",
                "composition",
                "cli",
                "remote",
                "provider",
                "provider_cli",
            )
        } | {"forgeai/py.typed"}
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
    # The installed ForgeAI sources import only public LegoAI modules, and
    # both Agents come from the installed engineering wheel.
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
        [
            str(python),
            "-I",
            "-c",
            "import forgeai, legoai_engineering.coding.api as c, "
            "legoai_engineering.reviewer.api as r; "
            "print(forgeai.__file__); print(c.__file__); print(r.__file__); "
            "print(c.CodingAgent.__name__, r.IndependentReviewer.__name__)",
        ],
        application,
    )
    *files, agents = probe.stdout.strip().splitlines()
    assert all(Path(file).is_relative_to(environment) for file in files)
    assert agents == "CodingAgent IndependentReviewer"
    # -I: no checkout, no PYTHONPATH, no user site; only the installed wheels.
    # The operator approves the one proposal explicitly on stdin.
    result = run([str(python), "-I", str(application / "demo.py")], application, "y\n")
    lines = result.stdout.splitlines()
    assert "disposition: succeeded" in lines, result.stdout
    assert any(line.startswith("Proposal (attempt 1, id ") for line in lines)
    assert "changed files: src/inventory/stock.py, tests/test_stock.py" in lines
    assert "check ruff_check: passed" in lines
    assert "check mypy: passed" in lines
    assert "check pytest: passed" in lines
    assert any(line.startswith("final HEAD: unchanged") for line in lines)
    # Two replay model calls: the Coding Agent, then the reviewer's ACCEPT.
    assert "review: accept" in lines
    assert not any(line.startswith("attempts:") for line in lines)
    assert "attempt count: 1" in lines
    # ForgeAI-3 bounded rework from the installed wheels: four replay calls
    # (coding, review CHANGES_REQUIRED, rework, review ACCEPT), two authorized
    # applies and two real sandboxed check passes.
    rework = run(
        [str(python), "-I", str(application / "demo.py"), "rework"],
        application,
        "y\ny\n",  # one explicit approval per proposal
    )
    lines = rework.stdout.splitlines()
    assert "disposition: succeeded" in lines, rework.stdout
    assert any(line.startswith("Rework proposal (attempt 2, id ") for line in lines)
    assert "attempts: 2 (one rework after review #1 required changes)" in lines
    assert "attempt 1 checks: ruff_check passed, mypy passed, pytest passed" in lines
    assert "attempt 1 review: changes_required" in lines
    assert "check pytest: passed" in lines
    assert any(line.startswith("final HEAD: unchanged") for line in lines)
    assert "review: accept" in lines
    assert (environment / "Scripts" / "forgeai.exe").is_file()
    assert sys.prefix != str(environment)
