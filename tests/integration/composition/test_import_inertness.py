"""F8b: import-inertness tests for the private composition root and the
deterministic reference module (Gate-1 plan SS12.1's inert-import
discipline; F8b task SS38).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_deterministic_and_composition_imports_are_inert(tmp_path: Path) -> None:
    script = """
import logging, sys
from unittest.mock import patch
handlers = tuple(logging.getLogger().handlers)
def denied(*args, **kwargs):
    raise AssertionError("import side effect")
def audit(event, args):
    if event.startswith(("socket.", "subprocess.", "sqlite3.")) or event in {
        "os.mkdir", "os.remove", "os.rename", "os.system"
    }:
        raise AssertionError(event)
sys.addaudithook(audit)
with patch.object(logging, "basicConfig", denied):
    import legoai.reference.deterministic
    import legoai.runtime
    import legoai.runtime._composition
    import legoai.runtime._composition.direct
    import legoai.execution
    import legoai.execution.values
    import legoai.resources
    import legoai.resources.values
    import legoai.governance.ports
    import legoai.reference.governance
    import legoai.plugins.ports
    import legoai.reference.plugins
    import legoai.capabilities.ports
    import legoai.reference.catalog
    import legoai.reference.resolution
    import legoai.evidence.ports
    import legoai.reference.evidence
    import legoai.execution.ports
    import legoai.reference.execution
assert tuple(logging.getLogger().handlers) == handlers
"""
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert list(tmp_path.iterdir()) == []
