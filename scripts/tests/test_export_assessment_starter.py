"""Filesystem safety and standalone independence, no package installation."""

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.export_assessment_starter import ROOT, export


def test_export_is_standalone_and_runs_without_site_packages(tmp_path: Path) -> None:
    destination = export(tmp_path / "generated")
    files = [p for p in destination.rglob("*") if p.is_file()]
    assert files
    assert not any("legoai." in p.read_text(encoding="utf-8") for p in files)
    assert not (destination / ".git").exists()
    script = """
import asyncio, sys
sys.path.insert(0, sys.argv[1])
from app.application.answer_service import AnswerService
from app.fixtures import make_model
from app.model import ChatRequest, ChatResult
assert 'offline answer' in asyncio.run(AnswerService(make_model()).answer('Hello'))
for factory, arg in ((ChatRequest, ()), (ChatRequest, []), (ChatResult, 1)):
    try:
        factory(arg)
    except (TypeError, ValueError):
        pass
    else:
        raise AssertionError('invalid contract accepted')
assert not any(name.startswith('legoai') for name in sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", script, str(destination / "backend/src")],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_refuses_existing_destination(tmp_path: Path) -> None:
    destination = tmp_path / "existing"
    destination.mkdir()
    sentinel = destination / "README.md"
    sentinel.write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="exists"):
        export(destination)
    assert sentinel.read_text() == "keep"


def test_force_preserves_unrelated_files(tmp_path: Path) -> None:
    destination = export(tmp_path / "generated")
    sentinel = destination / "private.env"
    sentinel.write_text("keep", encoding="utf-8")
    (destination / "README.md").write_text("modified", encoding="utf-8")
    export(destination, force=True)
    assert sentinel.read_text() == "keep"
    assert "Standalone" in (destination / "README.md").read_text()


@pytest.mark.parametrize("destination", [ROOT, ROOT.parent, ROOT / "exports"])
def test_source_repository_is_protected(destination: Path) -> None:
    with pytest.raises(ValueError, match="source repository"):
        export(destination, force=True)


def test_preflight_prevents_partial_overwrite(tmp_path: Path) -> None:
    destination = tmp_path / "generated"
    destination.mkdir()
    sentinel = destination / "README.md"
    sentinel.write_text("keep", encoding="utf-8")
    (destination / "backend").write_text("not a directory", encoding="utf-8")
    with pytest.raises(ValueError, match="parent"):
        export(destination, force=True)
    assert sentinel.read_text() == "keep"


def test_hardlinked_output_is_rejected(tmp_path: Path) -> None:
    destination = export(tmp_path / "generated")
    original = destination / "README.md"
    alias = tmp_path / "alias"
    alias.hardlink_to(original)
    with pytest.raises(ValueError, match="unshared"):
        export(destination, force=True)
    assert alias.read_bytes() == original.read_bytes()
