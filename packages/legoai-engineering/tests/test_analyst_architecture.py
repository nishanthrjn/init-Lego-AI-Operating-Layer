"""Analyst dependency controls and inert imports; no hostile Python claim."""

import subprocess
import sys
from pathlib import Path


def test_analyst_import_has_no_acquisition_or_invocation(tmp_path: Path) -> None:
    script = """
import os, sys, threading, dataclasses, json, hashlib
from unittest.mock import patch
def denied(*args, **kwargs):
    raise AssertionError('import effect')
def audit(event, args):
    if event == 'open':
        path, mode, flags = args
        if not isinstance(path, str) or not path.endswith(('.py', '.pyc')):
            raise AssertionError('non-code read')
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC):
            raise AssertionError('write')
    if event.startswith(('socket.', 'subprocess.')) or event in {'os.mkdir', 'os.remove', 'os.system'}:
        raise AssertionError(event)
sys.addaudithook(audit)
with patch.object(os, 'getenv', denied), patch.object(type(os.environ), '__getitem__', denied), patch.object(threading.Thread, 'start', denied):
    import legoai_engineering.analyst.values
    import legoai_engineering.analyst.api
    import legoai_engineering.analyst._composition
    import legoai_engineering.reviewer.values
    import legoai_engineering.reviewer.definition
    import legoai_engineering.reviewer.api
    import legoai_engineering.coding.definition
    import legoai_engineering.coding.values
    import legoai_engineering.coding.api
    import legoai_engineering.coding._composition
assert 'legoai_engineering.repository.local' not in sys.modules
assert 'legoai.reference.model' not in sys.modules
assert 'legoai_engineering.sandbox.docker' not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
