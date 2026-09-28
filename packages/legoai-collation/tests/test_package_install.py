"""Build and isolated wheel use; needs ``uv`` and the synced build tools."""

import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

PACK = Path(__file__).resolve().parents[1]
MODULES = {
    "legoai_collation/__init__.py",
    "legoai_collation/py.typed",
    "legoai_collation/_decimal.py",
    "legoai_collation/errors.py",
    "legoai_collation/values.py",
    "legoai_collation/normalize.py",
    "legoai_collation/reading.py",
    "legoai_collation/collation.py",
}


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, timeout=120, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def test_build_inventory_and_fresh_install(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    run(["uv", "build", "--no-build-isolation", "--out-dir", str(artifacts)], PACK)
    wheels = list(artifacts.glob("*.whl"))
    archives = list(artifacts.glob("*.tar.gz"))
    assert len(wheels) == len(archives) == 1
    with zipfile.ZipFile(wheels[0]) as wheel:
        names = wheel.namelist()
        assert {name for name in names if ".dist-info/" not in name} == MODULES
        metadata = wheel.read(
            next(name for name in names if name.endswith(".dist-info/METADATA"))
        ).decode("utf-8")
        assert "Requires-Dist:" not in metadata
        assert "Requires-Python: >=3.14,<3.15" in metadata or (
            "Requires-Python: <3.15,>=3.14" in metadata
        )
    with tarfile.open(archives[0]) as archive:
        paths = {name.partition("/")[2] for name in archive.getnames()}
        ignore = next(m for m in archive.getmembers() if m.name.endswith("/.gitignore"))
        handle = archive.extractfile(ignore)
        assert handle is not None
        shipped_ignore = handle.read()
    # Exact inventory: nothing from outside the pack may enter the sdist.
    assert paths == {
        *(f"src/{name}" for name in MODULES),
        *(f"tests/{path.name}" for path in (PACK / "tests").glob("*.py")),
        "examples/station_reading.py",
        "README.md",
        "pyproject.toml",
        "PKG-INFO",
        ".gitignore",
    }
    # Hatchling always ships the nearest .gitignore; it must be the pack's own.
    assert shipped_ignore == (PACK / ".gitignore").read_bytes()

    environment = tmp_path / "installed"
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / (
        "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    )
    run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(python),
            "--offline",
            "--no-deps",
            str(wheels[0]),
        ],
        tmp_path,
    )
    script = """
import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
import legoai_collation as c
assert Path(c.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
assert importlib.util.find_spec('legoai') is None
context = c.ComparisonContext('s', 'f')
policy = c.PrecedencePolicy('p/1', ((c.SourceId('a'), 0),))
reading = c.Reading(
    c.SourceRef(c.SourceId('a')), context, c.RawInput.of('1.50'), c.DecimalRule()
)
result = c.collate_field(context, (reading,), policy)
assert result.status is c.CollationStatus.AGREED
assert result.selected == Decimal('1.5')
print('installed collation ok')
"""
    result = run([str(python), "-I", "-B", "-c", script], tmp_path)
    assert result.stdout.strip() == "installed collation ok"
