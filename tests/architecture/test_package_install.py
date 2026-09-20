"""ADR-001/002 and F0: typing, inert imports and actual built-wheel isolation."""

import os
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, timeout=120, check=False
    )


def test_cross_kind_typing(tmp_path: Path) -> None:
    fixture = tmp_path / "identity_misuse.py"
    fixture.write_text(
        "from legoai.kernel.identity import TenantId, PrincipalId\n"
        "def tenant(value: TenantId) -> None: ...\n"
        "def principal(value: PrincipalId) -> None: ...\n"
        "tenant(TenantId('ok'))\nprincipal(PrincipalId('ok'))\n"
        "tenant(PrincipalId('wrong'))\nprincipal(TenantId('wrong'))\n",
        encoding="utf-8",
    )
    result = run(
        [sys.executable, "-m", "mypy", "--strict", "--no-incremental", str(fixture)],
        tmp_path,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    errors = [line for line in result.stdout.splitlines() if ": error:" in line]
    assert len(errors) == 2, result.stdout
    assert all("[arg-type]" in error for error in errors)
    assert 'incompatible type "PrincipalId"; expected "TenantId"' in errors[0]
    assert 'incompatible type "TenantId"; expected "PrincipalId"' in errors[1]


def test_inert_import(tmp_path: Path) -> None:
    # Preload stdlib dependencies; then observe only our package import interval.
    script = """
import dataclasses, logging, threading, socket, os, sys
from unittest.mock import patch
handlers = tuple(logging.getLogger().handlers)
threads = tuple(threading.enumerate())
def denied(*args, **kwargs):
    raise AssertionError("import side effect")
def audit(event, args):
    if event == "open":
        path, mode, flags = args
        if not isinstance(path, str) or not path.endswith((".py", ".pyc")):
            raise AssertionError("non-code file access")
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            raise AssertionError("file write")
    if event.startswith(("socket.", "subprocess.", "sqlite3.")) or event in {"os.mkdir", "os.remove", "os.rename", "os.system"}:
        raise AssertionError(event)
sys.addaudithook(audit)
with patch.object(threading.Thread, "start", denied), patch.object(logging, "basicConfig", denied), patch.object(os, "getenv", denied), patch.object(type(os.environ), "__getitem__", denied):
    import legoai
    import legoai.kernel
    import legoai.kernel.identity
assert tuple(logging.getLogger().handlers) == handlers
assert tuple(threading.enumerate()) == threads
assert not any(name.startswith("legoai.") and not name.startswith("legoai.kernel") for name in sys.modules)
"""
    result = run([sys.executable, "-I", "-B", "-c", script], tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert list(tmp_path.iterdir()) == []


def test_build_and_fresh_wheel(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    artifacts = tmp_path / "artifacts"
    result = run(
        ["uv", "build", "--no-build-isolation", "--out-dir", str(artifacts)], root
    )
    assert result.returncode == 0, result.stdout + result.stderr
    wheels = list(artifacts.glob("*.whl"))
    archives = list(artifacts.glob("*.tar.gz"))
    assert len(wheels) == len(archives) == 1
    expected = {
        "legoai/__init__.py",
        "legoai/kernel/__init__.py",
        "legoai/kernel/identity.py",
        "legoai/py.typed",
    }
    with zipfile.ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())
        assert {
            n for n in names if not n.split("/")[0].endswith(".dist-info")
        } == expected
        metadata = wheel.read(
            next(n for n in names if n.endswith("/METADATA"))
        ).decode()
        assert "Requires-Dist:" not in metadata
        assert "Requires-Python: <3.15,>=3.14" in metadata
    with tarfile.open(archives[0], "r:gz") as archive:
        names = {
            str(Path(n).relative_to(Path(n).parts[0])).replace("\\", "/")
            for n in archive.getnames()
        }
        assert {f"src/{n}" for n in expected} <= names
        assert all(
            not any(
                part in {".venv", "__pycache__", "planning", ".git"}
                for part in Path(n).parts
            )
            for n in names
        )
        assert names == {f"src/{n}" for n in expected} | {
            "pyproject.toml",
            "uv.lock",
            ".python-version",
            "PKG-INFO",
            ".gitignore",
            "docs/development.md",
            "tests/unit/kernel/test_identity.py",
            "tests/architecture/test_import_boundaries.py",
            "tests/architecture/test_package_install.py",
        }
    environment = tmp_path / "installed"
    venv.EnvBuilder(with_pip=False).create(environment)
    interpreter = environment / (
        "Scripts/python.exe" if os.name == "nt" else "bin/python"
    )
    result = run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(interpreter),
            "--no-deps",
            "--offline",
            str(wheels[0]),
        ],
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    script = """
import sys
from pathlib import Path
from importlib.metadata import version, requires
import legoai.kernel.identity as identity
assert Path(identity.__file__).is_relative_to(Path(sys.prefix))
assert identity.TenantId("abc").value == "abc"
assert identity.PrincipalId("abc").value == "abc"
assert version("legoai-reference") == "0.1.0.dev0"
assert not requires("legoai-reference")
assert Path(identity.__file__).parents[1].joinpath("py.typed").is_file()
"""
    result = run([str(interpreter), "-I", "-B", "-c", script], tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
